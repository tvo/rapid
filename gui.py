#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt4 import QtCore, QtGui
import models

class RapidListWidget(QtGui.QWidget):
	"""mostly based on the bascisortfiltermodel example from PyQt distribution"""
	def __init__(self,parent):
		super(RapidListWidget, self).__init__(parent)

		self.proxyModel = QtGui.QSortFilterProxyModel()
		self.proxyModel.setDynamicSortFilter(True)

		self.proxyView = QtGui.QTreeView()
		self.proxyView.setRootIsDecorated(False)
		self.proxyView.setAlternatingRowColors(True)
		self.proxyView.setModel(self.proxyModel)
		self.proxyView.setSortingEnabled(True)
		self.proxyModel.setSourceModel(models.RapidModel(self))
		self.proxyView.sortByColumn(0, QtCore.Qt.AscendingOrder)

		mainLayout = QtGui.QVBoxLayout()
		mainLayout.addWidget(self.proxyView)
		self.setLayout(mainLayout)

class RapidGUI(QtGui.QMainWindow):
	def __init__(self):
		QtGui.QMainWindow.__init__(self)
		self.setCentralWidget(RapidListWidget(self))		

if __name__ == '__main__':
	app = QtGui.QApplication(['RapidGUI'])
	window = RapidGUI()
	window.show()
	app.exec_()
