#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt4 import QtCore, QtGui
import models

class RapidListWidgetBase(QtGui.QWidget):
	"""mostly based on the bascisortfiltermodel example from PyQt distribution"""
	def __init__(self,parent):
		super(RapidListWidgetBase, self).__init__(parent)

		self.proxyModel = QtGui.QSortFilterProxyModel()
		self.proxyModel.setDynamicSortFilter(True)

		self.proxyView = QtGui.QTreeView()
		self.proxyView.setRootIsDecorated(False)
		self.proxyView.setAlternatingRowColors(True)
		self.proxyView.setModel(self.proxyModel)
		self.proxyView.setSortingEnabled(True)
		self.proxyView.sortByColumn(0, QtCore.Qt.AscendingOrder)
		
		mainLayout = QtGui.QVBoxLayout()
		mainLayout.addWidget(self.proxyView)
		self.setLayout(mainLayout)

class InstalledRapidListWidget(RapidListWidgetBase):
	def __init__(self,parent):
		super(InstalledRapidListWidget, self).__init__(parent)
		self.sourceModel = models.InstalledRapidModel(self)
		self.proxyModel.setSourceModel( self.sourceModel )
		self.sourceModel.reload()

class AvailableRapidListWidget(RapidListWidgetBase):
	def __init__(self,parent):
		super(AvailableRapidListWidget, self).__init__(parent)
		self.sourceModel = models.AvailableRapidModel(self)
		self.proxyModel.setSourceModel( self.sourceModel )
		self.sourceModel.reload()

class MainRapidWidget(QtGui.QWidget):
	def __init__(self,parent):
		super(MainRapidWidget, self).__init__(parent)
		self.availableWidget = AvailableRapidListWidget(self)
		self.installedWidget = InstalledRapidListWidget(self)
		mainLayout = QtGui.QHBoxLayout(self)
		mainLayout.addWidget( self.availableWidget )
		mainLayout.addWidget( self.installedWidget )
		self.setLayout( mainLayout )
		self.setMinimumSize(1034,768)

class RapidGUI(QtGui.QMainWindow):
	def __init__(self):
		QtGui.QMainWindow.__init__(self)
		self.mainWidget = MainRapidWidget(self)
		self.setCentralWidget(self.mainWidget)

if __name__ == '__main__':
	app = QtGui.QApplication(['RapidGUI'])
	window = RapidGUI()
	window.show()
	app.exec_()
