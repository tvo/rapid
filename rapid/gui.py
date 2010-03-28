#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys, main, models
from PyQt4 import QtCore, QtGui

class DownloadDialog(QtGui.QProgressDialog):
	def __init__(self,parent,tag):
		super(DownloadDialog, self).__init__('Downloading %s'%tag, QtCore.QString(), 0, 100, parent )
		self.dt = DownloadThread(tag)
		#we need to get changes via signals, cause accessing GUI from non-gui thread is not safe
		self.connect( self.dt, QtCore.SIGNAL("incrementValue"), self.incrementValue, QtCore.Qt.QueuedConnection )
		self.connect( self.dt, QtCore.SIGNAL("setMaximum"), self.setMaximum, QtCore.Qt.QueuedConnection )
		self.connect( self.dt, QtCore.SIGNAL("downloadComplete"), self.close, QtCore.Qt.QueuedConnection )
		self.dt.start()

	def incrementValue(self,value):
		self.setValue( self.value() + value )

	def setMaximum(self, value):
		super(DownloadDialog, self).setMaximum( value )

class DownloadThread(QtCore.QThread):
	def __init__(self, tag_or_name):
		QtCore.QThread.__init__(self)
		self.tag_or_name = tag_or_name
		self.max = 0
		print (self.tag_or_name)

	def install_single(self, p, dep = False):
		""" Install a single package and its dependencies."""
		for d in p.dependencies:
			self.install_single(d, True)
		if not p.installed():
			print ['Installing: ', 'Installing dependency: '][int(dep)] + p.name
			p.install(self)
			print
		elif not dep:
			print 'Already installed: ' + p.name

	def __call__(self, value ):
		self.emit( QtCore.SIGNAL("incrementValue"), value )

	def setMaximum(self, value ):
		self.max = value
		self.emit( QtCore.SIGNAL("setMaximum"), value )

	def maximum(self):
		return self.max

	def run(self):
		#FIXME: we get multiple tags. Which do we choose?
		try:
			p = main.rapid.packages()[self.tag_or_name.split(',')[0]]
		except KeyError:
			p = main.rapid.packages()[self.tag_or_name]
		self.install_single(p)
		self.emit( QtCore.SIGNAL("downloadComplete") )

class RapidListWidgetBase(QtGui.QWidget):
	"""mostly based on the bascisortfiltermodel example from PyQt distribution"""
	def __init__(self,parent):
		super(RapidListWidgetBase, self).__init__(parent)
		self.parent = parent
		self.proxyModel = QtGui.QSortFilterProxyModel()
		self.proxyModel.setDynamicSortFilter(True)

		self.proxyView = QtGui.QTreeView()
		self.proxyView.setRootIsDecorated(False)
		self.proxyView.setAlternatingRowColors(True)
		self.proxyView.setModel(self.proxyModel)
		self.proxyView.setSortingEnabled(True)
		self.proxyView.sortByColumn(0, QtCore.Qt.AscendingOrder)
		self.proxyView.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
		mainLayout = QtGui.QVBoxLayout()
		mainLayout.addWidget(self.proxyView)
		self.setLayout(mainLayout)

class InstalledRapidListWidget(RapidListWidgetBase):
	def __init__(self,parent):
		super(InstalledRapidListWidget, self).__init__(parent)
		self.sourceModel = models.InstalledRapidModel(self)
		self.proxyModel.setSourceModel( self.sourceModel )
		self.sourceModel.reload()
		self.proxyView.doubleClicked.connect(self.doubleClicked)

	def doubleClicked(self,modelIndex):
		item = self.sourceModel.itemFromIndex( self.proxyModel.mapToSource( modelIndex ) )

class AvailableRapidListWidget(RapidListWidgetBase):
	def __init__(self,parent):
		super(AvailableRapidListWidget, self).__init__(parent)
		self.sourceModel = models.AvailableRapidModel(self)
		self.proxyModel.setSourceModel( self.sourceModel )
		self.sourceModel.reload()
		self.proxyView.doubleClicked.connect(self.doubleClicked)

	def doubleClicked(self,modelIndex):
		item = self.sourceModel.itemFromIndex( self.proxyModel.mapToSource( modelIndex ) )
		tag = str(item.text())
		print 'downloading ',tag
		self.dl = DownloadDialog(window,tag)
		self.dl.show()
		self.connect( self.dl.dt, QtCore.SIGNAL("downloadComplete"), self.parent.reload, QtCore.Qt.QueuedConnection )

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

	def reload(self):
		self.availableWidget.sourceModel.reload()
		self.installedWidget.sourceModel.reload()

class RapidGUI(QtGui.QMainWindow):
	def __init__(self):
		QtGui.QMainWindow.__init__(self)
		self.mainWidget = MainRapidWidget(self)
		self.setCentralWidget(self.mainWidget)