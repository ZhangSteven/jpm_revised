# coding=utf-8
# 
# Read holdings and cash data from JPM bank statements and convert them into
# Geneva format.
#
from tester.file import itemGroup
from jpm_revised.utility import getCurrentDirectory
from utils.iter import head
from utils.excel import worksheetToLines
from xlrd import open_workbook
from operator import add
from functools import reduce
from itertools import filterfalse, islice
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
    dateString = readDateFromHeader(head(sections))   # consume the first section
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


    return extractDateString(head(filter(dateLine, lines))[0])



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

    sections = itemGroup(cashSection, lines[1:])    # consists of two sections
    return (readAccountCode(lines[0][0]) \
           , readHoldings(head(sections)) \
           , readCash(head(sections)))  



def readAccountCode(accountString):
    """
    [String] accountString => [String] accountCode

    The accountString looks like:
        Account:   53412   CLT CLI HK BR TRUST FUND CAPITAL

    The result would be:
        53412
    """
    return accountString.split(':')[1].split()[0]



def readHolding(lines):
    """
    [List] lines => [Iterable] holdings

    Where the lines of a holding section looks like:

    header lines
    holding 1
    holding 2
    """
    sections = itemGroup(emptyLine, lines)
    headers = readHeaders(head(sections))   # first section is the header
    return map(partial(readPosition, headers), sections)



def readHeaders(lines):
    """
    [List] lines => [List] headers

    The headers span across multiple lines, like

    Security ID Security Name           Location/Nominee    Awaiting Receipt ...                Reg./Sub Acct.  Awaiting Delivery   Current Face-Settled    Current Face-Total
    ISIN ... Coupon Rate Maturity Date   Pool Number Country Collateral Units        
    Borrowed Units      

    """
    return reduce(add, lines, [])   # simply concatenate all the lines together



def readPosition(headers, lines):
    """
    [List] headers, [List] lines => [Dictionary] position
    """
    allItems = reduce(add, filterfalse(emptyLine, lines), [])
    emptyHeader = lambda pair: emptyString(pair[0])
    return dict(filterfalse(emptyHeader, zip(headers, allItems)))



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
    for x in readHolding(islice(lines, 8, 22)):
        print(x)

