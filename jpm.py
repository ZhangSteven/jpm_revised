# coding=utf-8
# 
# Read holdings and cash data from JPM bank statements and convert them into
# Geneva format.
#

from jpm_revised.utility import getCurrentDirectory
from utils.iter import pop, itemGroup, firstOf
from utils.excel import worksheetToLines
from investment_lookup.id_lookup import get_investment_Ids, \
                                        lookup_investment_currency
from xlrd import open_workbook
from operator import add
from functools import reduce, partial
from itertools import filterfalse, islice, chain



emptyString = lambda x: True if isinstance(x, str) and x.strip() == '' else False
emptyLine = lambda line: all(emptyString(x) for x in line)



def readJPM(lines):
    """
    [Iterable] lines => [Tuple] (date, [Iterable] Accounts)

    From the lines of the JPM statement file, read out its date and a list of
    accounts.

    The worksheet consists of multiple accounts. The structure of data is like:

    Header lines (consist of date)

    Account 1 lines (consist of holding and cash)

    Account 2 lines
        ...
    """
    accountLine = lambda L: True if len(L) > 0 and str(L[0]).startswith('Account:') \
                            else False
    sections = itemGroup(accountLine, lines)
    dateString = dateFromHeader(pop(sections))   # consume the first section
    return reduce(chain
                 , map(partial(genevaPosition, dateString)
                      , map(account, sections))
                 , [])



def dateFromHeader(lines):
    """
    [Iterable] lines => [String] date

    From the header section of the JPM statement file, represented by a list of
    lines, extract the date of the statement.
    """
    dateLine = lambda L: True if len(L) > 0 and str(L[0]).startswith('As Of:') \
                            else False

    def extractDateString(s):
        temp_list = s.split(':')[1].strip().split('-')
        month = {'jan':'01', 'feb':'02', 'mar':'03', 'apr':'04', 
                    'may':'05', 'jun':'06', 'jul':'07', 'aug':'08', 
                    'sep':'09', 'oct':'10', 'nov':'11', 'dec':'12'}\
                    [temp_list[1].lower()]
        return temp_list[2] + '-' + month + '-' + temp_list[0]


    return extractDateString(pop(filter(dateLine, lines))[0])



def account(lines):
    """
    [List] lines => [Tuple] ([String] account code
                            , [Iterable] holdings
                            , [Iterable] cashEntries)

    There are two cases:

    (1) Normal case:
    Account line (account code, name)
    holding section (0 or 1 holding section):
        ...
    cash section (0 or 1 cash section):
        ...

    (2) Special case:
    Account line (account code, name)
    No data for this account (second line)

    """
    emptyAccount = lambda L: True if len(L) > 0 and L[0] == 'No Data for this Account' \
                                else False

    if emptyAccount(lines[1]):
        return ('', [])


    cashSection = lambda L: True if len(L) > 0 and L[0] == 'Branch Code' \
                                else False

    sections = itemGroup(cashSection, lines[1:])
    return (readAccountCode(lines[0][0])
           , chain(readPosition(pop(sections)), readPosition(pop(sections))))



def readAccountCode(accountString):
    """
    [String] accountString => [String] accountCode

    The accountString looks like:
        Account:   53412   CLT CLI HK BR TRUST FUND CAPITAL

    The result would be:
        53412
    """
    return accountString.split(':')[1].split()[0]



def readPosition(lines):
    """
    [List] lines => [Iterable] holdings

    Where a holding is a dictionary object representing a position.

    The lines could be a holding section or a cash section.

    header line(s)
    <empty line>
    lines for position 1
    <empty line>
    lines for position 2
    """
    if lines == None:
        return []

    sections = itemGroup(emptyLine, lines)
    headers = readHeaders(pop(sections))   # first section is the header
    return map(partial(position, headers), sections)



def readHeaders(lines):
    """
    [List] lines => [List] headers

    The headers can span across multiple lines, like in a holdings section:

    Security ID Security Name           Location/Nominee    Awaiting Receipt ...                Reg./Sub Acct.  Awaiting Delivery   Current Face-Settled    Current Face-Total
    ISIN ... Coupon Rate Maturity Date   Pool Number Country Collateral Units        
    Borrowed Units      

    Or it can be just one line, like in a cash section:

    Branch Code Branch Name         Cash Account    Cash Account Name
    """
    return reduce(add, lines, [])   # simply concatenate values in all the lines



def position(headers, lines):
    """
    [List] headers, [List] lines => [Dictionary] position

    line: a list of values
    """
    emptyHeader = lambda pair: emptyString(pair[0])
    toDictionary = lambda headers, values: dict(filterfalse(emptyHeader
                                                           , zip(headers, values)))

    return toDictionary(headers
                       , reduce(add, filterfalse(emptyLine, lines), []))



def genevaPosition(date, accountInfo):
    """
    [Sring] date, [Tuple] accountInfo => [Iterable] Geneva Position

    Where accountInfo is the outcome of the account() function, consisting of
    (accountCode, positions)

    Where a Geneva position is either a holding position or cash position
    depending on the input position
    """
    accountCode, positions = accountInfo

    def toGenevaPosition(position):
        if 'Security ID' in position:
            return genevaHolding(getPortId(accountCode), date, position)
        else:
            return genevaCash(getPortId(accountCode), date, position)


    return map(toGenevaPosition, positions)



def genevaHolding(portId, date, holding):
    """
    [String] portId, [String] date, [Dictionary] holding => 
        [Dictionary] gPosition
    
    A Geneva position is a dictionary object that has the following
    keys:

    portfolio|custodian|date|geneva_investment_id|ISIN|bloomberg_figi|name
    |currency|quantity
    
    """
    genevaPos = {}
    genevaPos['portfolio'] = portId
    genevaPos['custodian'] = getCustodian()
    genevaPos['date'] = date
    genevaPos['name'] = holding['Security Name']
    genevaPos['currency'] = getCurrency(holding['Security Name'], holding['Security ID'].strip())
    genevaPos['quantity'] = holding['Total Units']
    (genevaPos['geneva_investment_id'], genevaPos['ISIN'], genevaPos['bloomberg_figi']) \
                = getSecurityId(portId, holding['ISIN'].strip(), holding['Security ID'].strip())
    
    return genevaPos



def genevaCash(portId, date, cash):
    """
    [String] portId, [String] date, [Dictionary] cash => 
        [Dictionary] gCash

    A Geneva cash position is a dictionary object that has the following
    keys:

    portfolio|custodian|date|currency|balance
    
    """
    genevaCash = {}
    genevaCash['portfolio'] = portId
    genevaCash['custodian'] = getCustodian()
    genevaCash['date'] = date
    genevaCash['currency'] = cash['Local CCY']
    genevaCash['balance'] = cash['Closing Cash Balance']
    
    return genevaCash



def getSecurityId(portId, isin, securityId):
    """
    [String] portId, [String] isin, [String] securityId =>
        [Tuple] (geneva_investment_id, isin, bloomberg_figi)
    """
    if emptyString(isin):
        security_id_type = 'JPM'
        security_id = securityId
    else:
        security_id_type = 'ISIN'
        security_id = isin

    investment_ids = get_investment_Ids(portId, security_id_type, security_id)

    # For portfolio 12404, give special treatment for this position:
    # 
    # SINO-OCEAN GROUP HOLDING LTD COMMON STOCK HKD 0
    # with isin = 'HK3377040226'. 
    # 
    # Although it is a common stock, however, it is treated as private security 
    # in Geneva due to special accounting treatment.
    # 
    if portId == '12404' and investment_ids == ('', 'HK3377040226', ''):
        investment_ids = ('SINO OCEAN LAND_DUMMY', '', '')

    return investment_ids



def getCurrency(name, securityId):
    """
    [String] name => [String] currency
    """
    return currencyFromName(name) or lookup_investment_currency('JPM', securityId)



def currencyFromName(name):
    """
    Extract the currency from the security name

    [String] name => [String] currency

    security name looks like:

    HUI XIAN REAL ESTATE INVESTMENT TRUST REIT CNY

    PICC PROPERTY & CASUALTY CO LTD COMMON STOCK HKD 1

    1MDB ENERGY LTD NOTES FIXED 5.99% 11/MAY/2022 USD 100000
    """
    isCurrency = lambda x: x in ['HKD', 'USD', 'CNY', 'SGD', 'JPY', 'EUR']
    return firstOf(isCurrency, name.split()[-2:])



def getCustodian():
    return 'JPM'



def getPortId(accountCode):
    """
    Map the account code of JP Morgan to the portfolio id in Geneva.
    """
    p_map = {
        # China Life overseas accounts
        '48029': '11490',
        '48089': '12341',
        '48090': '12298',
        '48195': '12548',  # CLO trustee's bond fund
        '53412': '12857',
        '53413': '12856',
        '48194': '12726',

        # China Life ListCo accounts
        'AFU34': '12404',
        'AFU35': '12307',
        'BBK32': '12094',
        'AFU37': '12086',
        'AHS61': '12087'
    }

    try:
        return p_map[accountCode]
    except KeyError:
        logger.error('getPortId(): invalid account code {0}'.format(accountCode))
        raise ValueError



if __name__ == '__main__':
    from os.path import join
    inputFile = join(getCurrentDirectory(), 'samples', 'statement01.xls')

    lines = worksheetToLines(open_workbook(inputFile).sheet_by_index(0))
    # accountCode, positions = account(list(islice(lines, 7, 201)))
    # print(accountCode)
    # for x in positions:
    #     print(x)

    # for x in genevaPosition('2016-06-07', account(list(islice(lines, 7, 201)))):
    #     print(x)

    for x in readJPM(lines):
        print(x)