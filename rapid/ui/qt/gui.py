#!/usr/bin/env python

import os, sys
from rapid import main
import models
from PyQt4 import QtCore, QtGui
from rapid.ui.text.interaction import TextUserInteraction
from rapid.unitsync.api import get_writable_data_directory

def split_on_condition(seq, condition):
	#see http://stackoverflow.com/questions/949098/python-split-a-list-based-on-a-condition
	a, b = [], []
	for item in seq:
		(a if condition(item) else b).append(item)
	return a,b

class ReloadThread(QtCore.QThread):

	def __init__(self, mainWidget,options, parent = None):
		QtCore.QThread.__init__(self, parent)
		self.mainWidget = mainWidget
		self.options = options

	def stop(self):
		self.wait() # waits until run stops on his own

	def run(self):
		#progress = QtGui.QProgressDialog( "Loading data", "EUDE", 0, 0 )
		#progress.show()
		ui = TextUserInteraction()
		if self.options.datadir:
			main.init(options.datadir, ui)
		elif self.options.unitsync:
			main.init(get_writable_data_directory(), ui)
		elif os.name == 'posix':
			main.init(os.path.expanduser('~/.spring'), ui)
		else:
			print 'No data directory specified. Specify one using either --datadir or --unitsync.'
			print
		installed,available = split_on_condition( main.rapid.packages, lambda p: p.installed )
		self.mainWidget.reload( installed,available )
		#progress.destroy()
		self.stop()

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
		if not p.installed:
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
			p = main.rapid.packages[self.tag_or_name.split(',')[0]]
		except KeyError:
			p = main.rapid.packages[self.tag_or_name]
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
		self.filterEdit = QtGui.QLineEdit(self.parent)
		filterLabel = QtGui.QLabel( "Filter (Name):",self.parent ) 
		filterLayout = QtGui.QHBoxLayout()
		filterLayout.addWidget( filterLabel,stretch=0 )
		filterLayout.addWidget( self.filterEdit,stretch=1 )
		mainLayout = QtGui.QVBoxLayout()
		mainLayout.addWidget(self.proxyView,stretch=1)
		mainLayout.addLayout(filterLayout,stretch=0)
		self.setLayout(mainLayout)
		self.filterEdit.textChanged.connect( self.proxyModel.setFilterFixedString )

class InstalledRapidListWidget(RapidListWidgetBase):
	def __init__(self,parent):
		super(InstalledRapidListWidget, self).__init__(parent)
		self.sourceModel = models.InstalledRapidModel(self)
		self.proxyModel.setSourceModel( self.sourceModel )
		self.proxyView.doubleClicked.connect(self.doubleClicked)

	def doubleClicked(self,modelIndex):
		item = self.sourceModel.itemFromIndex( self.proxyModel.mapToSource( modelIndex ) )
		tag = str(item.text())
		#FIXME: we get multiple tags. Which do we choose?
		try:
			p = main.rapid.packages[tag.split(',')[0]]
		except KeyError:
			p = main.rapid.packages[tag.tag_or_name]
		
		if not p.can_be_uninstalled:
			msg = QtGui.QMessageBox(self.parent)
			#FIXME: this message is fubar
			msg.setText("There are tags installed that depend on the tag that is to be uninstalled.")
			msg.setInformativeText("Remove dependent tags?")
			msg.setStandardButtons(QtGui.QMessageBox.Ok |  QtGui.QMessageBox.Cancel)
			msg.setDefaultButton( QtGui.QMessageBox.Cancel )
			if msg.exec_() == QtGui.QMessageBox.Ok:
				for rdep in p.reverse_dependencies:
					rdep.uninstall()
			else :
				return
		try:
			p.uninstall()
			QtGui.QMessageBox.information( self.parent, "Done","%s was removed"%p.name )
			self.sourceModel.reload()
		except Exception, e:
			print e
			QtGui.QMessageBox.critical( self.parent, "Error", "Removing %s failed\n%s"%(p.name,str(e)) )
		

class AvailableRapidListWidget(RapidListWidgetBase):
	def __init__(self,parent):
		super(AvailableRapidListWidget, self).__init__(parent)
		self.sourceModel = models.AvailableRapidModel(self)
		self.proxyModel.setSourceModel( self.sourceModel )
		self.proxyView.doubleClicked.connect(self.doubleClicked)

	def doubleClicked(self,modelIndex):
		item = self.sourceModel.itemFromIndex( self.proxyModel.mapToSource( modelIndex ) )
		tag = str(item.text())
		print 'downloading ',tag
		self.dl = DownloadDialog(self.parent,tag)
		self.dl.show()
		self.connect( self.dl.dt, QtCore.SIGNAL("downloadComplete"), self.parent.reload, QtCore.Qt.QueuedConnection )

class MainRapidWidget(QtGui.QWidget):
	
	def __init__(self,parent):
		super(MainRapidWidget, self).__init__(parent)
		QtCore.QObject.connect(self, QtCore.SIGNAL("reload()"), reload)
		self.availableWidget = AvailableRapidListWidget(self)
		self.installedWidget = InstalledRapidListWidget(self)
		mainLayout = QtGui.QHBoxLayout(self)
		leftLayout = QtGui.QVBoxLayout(self)
		self.leftLabel = QtGui.QLabel("loading..", parent )
		leftLayout.addWidget( self.leftLabel, stretch=0 )
		leftLayout.addWidget( self.availableWidget, stretch=1 )
		rightLayout = QtGui.QVBoxLayout(self)
		self.rightLabel = QtGui.QLabel("loading..", parent )
		rightLayout.addWidget( self.rightLabel, stretch=0 )
		rightLayout.addWidget( self.installedWidget, stretch=1 )
		mainLayout.addLayout( leftLayout )
		mainLayout.addLayout( rightLayout )
		self.setLayout( mainLayout )

	def reload(self,installed,available):
		self.leftLabel.setText( "reloading..." )
		self.rightLabel.setText( "reloading..." )
		self.availableWidget.sourceModel.loadData( available )
		self.installedWidget.sourceModel.loadData( installed )
		self.leftLabel.setText("Availabe tags (double-click to install)")
		self.rightLabel.setText("Installed tags (double-click to uninstall)")

class RapidGUI(QtGui.QMainWindow):
	def __init__(self,options):
		QtGui.QMainWindow.__init__(self)
		settings = QtCore.QSettings()
		settings.beginGroup("MainWindow");
		self.resize(settings.value("size", QtCore.QSize(600, 480)).toSize());
		self.move(settings.value("pos", QtCore.QPoint(200, 200)).toPoint());
		settings.endGroup();
		self.mainWidget = MainRapidWidget(self)
		self.setCentralWidget(self.mainWidget)
		self.reloadThread = ReloadThread( self.mainWidget,options )
		self.reloadThread.start()
		
	def closeEvent (self, event):
		settings = QtCore.QSettings()
		settings.beginGroup("MainWindow");
		settings.setValue("size", self.size())
		settings.setValue("pos", self.pos())
		settings.endGroup()
