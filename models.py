#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt4 import QtCore, QtGui
import rapid,main

class BaseRapidModel(QtGui.QStandardItemModel):
	def __init__(self,parent):
		super(BaseRapidModel,self).__init__(parent)

	def reloadData(self, dataFunction):
		self.clear()
		self.setColumnCount(2)
		self.setRowCount(0)
		self.setHeaderData(0, QtCore.Qt.Horizontal, "Name")
		self.setHeaderData(1, QtCore.Qt.Horizontal, "Tags")
		i = 0
		for p in filter( dataFunction, main.rapid.get_packages() ):
			self.insertRow(i)
			self.setData(self.index(i, 0), p.name)
			self.setData(self.index(i, 1), ', '.join(p.tags))
			i += 1

class AvailableRapidModel(BaseRapidModel):
	def __init__(self,parent):
		super(AvailableRapidModel, self).__init__(parent)

	def reload(self):
		self.reloadData( lambda p: not p.installed() )

class InstalledRapidModel(BaseRapidModel):
	def __init__(self,parent):
		super(InstalledRapidModel, self).__init__(parent)

	def reload(self):
		self.reloadData( lambda p: p.installed() )