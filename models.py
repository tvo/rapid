#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PyQt4 import QtCore, QtGui
import rapid,main

class RapidModel(QtGui.QStandardItemModel):
	def __init__(self,parent):
		super(RapidModel,self).__init__(0, 2, parent)
		self.setHeaderData(0, QtCore.Qt.Horizontal, "Name")
		self.setHeaderData(1, QtCore.Qt.Horizontal, "Tag")
		i = 0
		for p in filter(lambda p: not p.installed(), main.rapid.get_packages() ):
			self.insertRow(i)
			self.setData(self.index(i, 0), p.name)
			self.setData(self.index(i, 1), p.tag)
			i += 1

