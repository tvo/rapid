#!/usr/bin/env python

from PyQt4 import QtCore, QtGui
from rapid import main

class BaseRapidModel(QtGui.QStandardItemModel):
	def __init__(self,parent):
		super(BaseRapidModel,self).__init__(parent)

	def reloadData(self, dataFunction):
		self.loadData( filter( dataFunction, main.rapid.packages ) )

	def loadData(self, package_list):
		self.clear()
		self.setColumnCount(2)
		self.setRowCount(0)
		self.setHeaderData(0, QtCore.Qt.Horizontal, "Name")
		self.setHeaderData(1, QtCore.Qt.Horizontal, "Tags")
		i = 0
		for p in package_list:
			self.insertRow(i)
			self.setData(self.index(i, 0), p.name)
			self.setData(self.index(i, 1), ', '.join(p.tags))
			i += 1

class AvailableRapidModel(BaseRapidModel):
	def __init__(self,parent):
		super(AvailableRapidModel, self).__init__(parent)

	def reload(self):
		self.reloadData( lambda p: not p.installed )

class InstalledRapidModel(BaseRapidModel):
	def __init__(self,parent):
		super(InstalledRapidModel, self).__init__(parent)

	def reload(self):
		self.reloadData( lambda p: p.installed )