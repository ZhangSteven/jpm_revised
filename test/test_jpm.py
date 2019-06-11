# coding=utf-8
# 

import unittest2
from functools import partial
from itertools import islice, filterfalse
from xlrd import open_workbook
from utils.excel import worksheetToLines
from jpm_revised.jpm import account, genevaPosition, readJPM
from jpm_revised.utility import getCurrentDirectory
from os.path import join



isHolding = lambda x: True if 'Security Name' in x else False



class TestJPM(unittest2.TestCase):

    def __init__(self, *args, **kwargs):
        super(TestJPM, self).__init__(*args, **kwargs)



    def testHolding(self):
        inputFile = join(getCurrentDirectory(), 'samples', 'statement01.xls')
        lines = worksheetToLines(open_workbook(inputFile).sheet_by_index(0))
        accountCode, positions = account(list(islice(lines, 7, 201)))
        holdings = list(filter(isHolding, positions))
        self.assertEqual(36, len(holdings))
        self.verifyHolding1(holdings[0])
        self.verifyHolding2(holdings[35])



    def testCash(self):
        inputFile = join(getCurrentDirectory(), 'samples', 'statement01.xls')
        lines = worksheetToLines(open_workbook(inputFile).sheet_by_index(0))
        accountCode, positions = account(list(islice(lines, 7, 201)))
        cash = list(filterfalse(isHolding, positions))
        self.assertEqual(3, len(cash))
        self.assertEqual('HKD', cash[1]['Local CCY'])
        self.assertAlmostEqual(1208208427.86, cash[1]['Opening Cash Balance'])
        self.assertAlmostEqual(1115935826.52, cash[1]['Closing Cash Balance'])



    def testGenevaPosition(self):
        inputFile = join(getCurrentDirectory(), 'samples', 'statement01.xls')
        lines = worksheetToLines(open_workbook(inputFile).sheet_by_index(0))
        dateString = '2016-07-06'
        positions = list(genevaPosition(dateString, account(list(islice(lines, 7, 201)))))
        self.assertEqual(39, len(positions))
        self.verifyGenevaHolding1(positions[0], dateString)
        self.verifyGenevaCash1(positions[38], dateString)



    def testReadJPM(self):
        inputFile = join(getCurrentDirectory(), 'samples', 'statement01.xls')
        (dateString, holdings, cashEntries) = \
            readJPM(worksheetToLines(open_workbook(inputFile).sheet_by_index(0)))
        self.assertEqual(len(holdings), 52)
        self.assertEqual(len(cashEntries), 10)
        self.assertEqual('2016-07-06', dateString)
        self.verifyGenevaHolding2(holdings[51], dateString)
        self.verifyGenevaCash2(cashEntries[9], dateString)



    def verifyHolding1(self, holding):
        self.assertEqual(18, len(holding))
        self.assertEqual(9917000, holding['Total Units'])
        self.assertEqual('KYG8875G1029  ', holding['ISIN'])
        self.assertEqual('KY', holding['Country'])
        self.assertEqual('3SBIO INC COMMON STOCK HKD 0.00001', holding['Security Name'])



    def verifyHolding2(self, holding):
        self.assertEqual(18, len(holding))
        self.assertEqual(150000, holding['Settled Units'])
        self.assertEqual('B1L3XL6  ', holding['Security ID'])
        self.assertEqual('ZHUZHOU CRRC TIMES ELECTRIC CO LTD', holding['Security Name'])



    def verifyGenevaHolding1(self, position, dateString):
        self.assertEqual(9, len(position))
        self.assertEqual('11490', position['portfolio'])
        self.assertEqual('JPM', position['custodian'])
        self.assertEqual(dateString, position['date'])
        self.assertEqual('HKD', position['currency'])
        self.assertEqual(9917000, position['quantity'])
        self.assertEqual('3SBIO INC COMMON STOCK HKD 0.00001', position['name'])
        self.assertEqual('KYG8875G1029', position['ISIN'])
        self.assertEqual('', position['geneva_investment_id'])
        self.assertEqual('', position['bloomberg_figi'])



    def verifyGenevaCash1(self, position, dateString):
        self.assertEqual(5, len(position))
        self.assertEqual('11490', position['portfolio'])
        self.assertEqual('JPM', position['custodian'])
        self.assertEqual(dateString, position['date'])
        self.assertEqual('USD', position['currency'])
        self.assertAlmostEqual(57221400.84, position['balance'])



    def verifyGenevaHolding2(self, position, dateString):
        self.assertEqual(9, len(position))
        self.assertEqual('12856', position['portfolio'])
        self.assertEqual('JPM', position['custodian'])
        self.assertEqual(dateString, position['date'])
        self.assertEqual('HKD', position['currency'])
        self.assertEqual(7683000, position['quantity'])
        self.assertEqual('CHINA LONGYUAN POWER GROUP CORP LTD COMMON STOCK HKD 1', position['name'])
        self.assertEqual('CNE100000HD4', position['ISIN'])
        self.assertEqual('', position['geneva_investment_id'])
        self.assertEqual('', position['bloomberg_figi'])



    def verifyGenevaCash2(self, position, dateString):
        self.assertEqual(5, len(position))
        self.assertEqual('12856', position['portfolio'])
        self.assertEqual('JPM', position['custodian'])
        self.assertEqual(dateString, position['date'])
        self.assertEqual('USD', position['currency'])
        self.assertAlmostEqual(906.48, position['balance'])