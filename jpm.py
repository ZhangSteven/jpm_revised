# coding=utf-8
# 
# Read holdings and cash data from JPM bank statements and convert them into
# Geneva format.
#
from tester.file import itemGroup
from jpm_revised.utility import getCurrentDirectory
from utils.iter import pop
from utils.excel import worksheetToLines
from xlrd import open_workbook
from operator import add
from functools import reduce
from itertools import filterfalse, islice, chain
from functools import partial



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
    dateString = readDateFromHeader(pop(sections))   # consume the first section
    return dateString




def readDateFromHeader(lines):
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
    holding section:
        ...
    cash section:
        ...

    (2) Special case:
    Account line (account code, name)
    No data for this account

    """
    emptyAccount = lambda L: True if len(L) > 0 and L[0] == 'No Data for this Account' \
                                else False

    if emptyAccount(lines[1]):
        return ('', [], [])


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
    emptyHeader = lambda pair: emptyString(pair[0])
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
    return toDictionary(headers
                       , reduce(add, filterfalse(emptyLine, lines), []))



def toDictionary(headers, values):
    emptyHeader = lambda pair: emptyString(pair[0])
    return dict(filterfalse(emptyHeader, zip(headers, values)))



def emptyString(x):
    if isinstance(x, str) and x.strip() == '':
        return True
    else:
        return False



def emptyLine(line):
    """
    [List] line => [Bool] is all the cell empty
    """
    return all(emptyString(x) for x in line)



def portfolioId(accountCode):
    """
    [String] accountCode => [String] portfolioId

    Map account code from JPM to portfolio id in Geneva
    """
    return 'TestPortId' #FIXME




if __name__ == '__main__':
    from os.path import join
    inputFile = join(getCurrentDirectory(), 'samples', 'statement01.xls')

    lines = worksheetToLines(open_workbook(inputFile).sheet_by_index(0))
    # for x in readPosition(islice(lines, 8, 22)):
    #     print(x)

    # for x in readPosition(islice(lines, 194, 201)):
    #     print(x)

    accountCode, positions = account(list(islice(lines, 7, 201)))
    print(accountCode)
    for x in positions:
        print(x)
