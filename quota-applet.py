#!/usr/bin/python
# Fri Apr 1 2011 Thomas Uphill <uphill@ias.edu>

import pygtk
pygtk.require('2.0')
import gtk
import quota
import thread
import threading
import pynotify
import sys


from quota_applet_images import redDisk
from quota_applet_images import yellowDisk
from quota_applet_images import greenDisk
redPixbuf = gtk.gdk.pixbuf_new_from_xpm_data(redDisk)
yellowPixbuf = gtk.gdk.pixbuf_new_from_xpm_data(yellowDisk)
greenPixbuf = gtk.gdk.pixbuf_new_from_xpm_data(greenDisk)

#gtk.gdk.threads_init()

# warning levels
red = 75
yellow = 50

# time between updates in seconds
interval = 600

def quotainfo(fs,b,f,bu,bq,fu,fq):
	global red
	global yellow
	
	frame = gtk.Frame()
	frame.set_label(fs)
	frame.set_border_width(10)
	table = gtk.Table(2,2,True)
	table.set_border_width(5)
	frame.add(table)

	blocks = gtk.Label("Blocks")
	blocks.set_alignment(0,0.5)
	table.attach(blocks,0,1,0,1)
	blocks.show()

	status = gtk.Image()
	if (b > red): status.set_from_pixbuf(redPixbuf)
	elif (b > yellow): status.set_from_pixbuf(yellowPixbuf)
	else: status.set_from_pixbuf(greenPixbuf)
	table.attach(status, 1, 2, 0, 1)
	status.show()

	percent = gtk.Label("%s%%" % b)
	percent.set_alignment(0.9,0.3)
	table.attach(percent,2,3,0,1)
	percent.show()

	percent = gtk.Label("%s/%s" % (bu,bq))
	percent.set_alignment(0.9,0.7)
	table.attach(percent,2,3,0,1)
	percent.show()

	files = gtk.Label("Files")
	files.set_alignment(0,0.5)
	table.attach(files,0,1,1,2)
	files.show()

	status = gtk.Image()
	if (f > red): status.set_from_pixbuf(redPixbuf)
	elif (f > yellow): status.set_from_pixbuf(yellowPixbuf)
	else: status.set_from_pixbuf(greenPixbuf)
	table.attach(status, 1, 2, 1, 2)
	status.show()

	percent = gtk.Label("%s%%" % f)
	percent.set_alignment(0.9,0.3)
	table.attach(percent,2,3,1,2)
	percent.show()
	
	percent = gtk.Label("%s/%s" % (fu,fq))
	percent.set_alignment(0.9,0.7)
	table.attach(percent,2,3,1,2)
	percent.show()
	
	table.show()
	return frame

class TaskThread(threading.Thread):
	def __init__(self,icon):
		threading.Thread.__init__(self)
		self._finished = threading.Event()
		self._interval = 300
		self.icon = icon
		self.warning = 0

	def shutdown(self):
		self._finished.set()

	def setInterval(self,interval):
		self._interval = interval

	def run(self):
		while 1:
			if self._finished.isSet(): return
			self.task()

			self._finished.wait(self._interval)

	def task(self):
		"""
		run periodically and change the status icon based on quota reported.
		"""
		q = quota.Quota()
		percent = 0
		message = ""
		warning = 0
		global red
		global yellow
		# loop through fs, update percent to change icon, if warning, then update message
		for fs in q.filesystems:
			for x in ['blocks','files']:
				warntype = None
				if (percent < q.filesystems[fs][x]['percentage']):
					percent = q.filesystems[fs][x]['percentage']
				if (q.filesystems[fs][x]['percentage'] > red):
					warntype = "Warning"
				elif (q.filesystems[fs][x]['percentage'] > yellow):
					warntype = "Caution"
				if (warntype):
					message = message + "<b>%s:</b> %s%% %s quota used on %s\n Limit %s, usage %s\n" \
						% (warntype,q.filesystems[fs][x]['percentage'],x, fs, q.filesystems[fs][x]['quota'], q.filesystems[fs][x]['usage'])
		if (percent > red):
			title = "Quota - Warning"
			warning = 1
			self.icon.set_from_pixbuf(redPixbuf)
		elif (percent > yellow):
			title = "Quota - Caution" 
			warning = 1
			self.icon.set_from_pixbuf(yellowPixbuf)
		else:
			self.icon.set_from_pixbuf(greenPixbuf)

		# popup the notification if we are in warning state

		if (warning):
			if (pynotify.init("Quota Violation")):
				try:
					self.n.update(title, message,"dialog-warning")
				except:
					self.n = pynotify.Notification(title, message, "dialog-warning")
					self.n.set_urgency(pynotify.URGENCY_NORMAL)
					self.n.set_timeout(pynotify.EXPIRES_NEVER)
					self.n.attach_to_status_icon(self.icon)
				self.n.show()

class QuotaNotification:
  global interval

  def __init__(self):
    self.statusIcon = gtk.StatusIcon()
    self.statusIcon.set_from_stock(gtk.STOCK_APPLY)
    self.statusIcon.set_visible(True)
    self.statusIcon.set_tooltip("Quota Notification")

    self.menu = gtk.Menu()
    self.menuItem = gtk.ImageMenuItem(gtk.STOCK_ABOUT)
    self.menuItem.connect('activate', self.about, self.statusIcon)
    self.menu.append(self.menuItem)
    self.menuItem = gtk.ImageMenuItem(gtk.STOCK_HELP)
    self.menuItem.get_children()[0].set_label('Quota Information')
    self.menuItem.connect('activate', self.show_quota, self.statusIcon)
    self.menu.append(self.menuItem)
    self.menuItem = gtk.ImageMenuItem(gtk.STOCK_QUIT)
    self.menuItem.connect('activate', self.quit, self.statusIcon)
    self.menu.append(self.menuItem)

    self.statusIcon.connect('popup-menu', self.popup_menu_cb, self.menu)
    self.statusIcon.set_visible(1)

    gtk.gdk.threads_init()
    self.t = TaskThread(self.statusIcon)
    self.t.setInterval(interval)
    threading.Thread(target=self.t.run, args=()).start()
    thread.start_new_thread(gtk.main,())

  def show_quota(self, widget, event, data = None):
    window = gtk.Window(gtk.WINDOW_TOPLEVEL)
    window.set_border_width(10)
    window.set_title("Quota Information")

    ok = gtk.Button("Ok")
    ok.connect_object("clicked", gtk.Widget.destroy, window)

    box = gtk.VBox()

    # get our quota
    q = quota.Quota()
    for fs in q.filesystems:
      fsFrame = quotainfo(fs,q.filesystems[fs]['blocks']['percentage'],q.filesystems[fs]['files']['percentage'],\
				q.filesystems[fs]['blocks']['usage'],q.filesystems[fs]['blocks']['quota'], \
				q.filesystems[fs]['files']['usage'],q.filesystems[fs]['files']['quota'])
      box.pack_start(fsFrame)
      fsFrame.show()

    box.pack_start(ok)
    ok.show()
    window.add(box)
    box.show()
    window.show()

  def about(self, widget, event, data = None):
    window = gtk.Window(gtk.WINDOW_TOPLEVEL)
    window.set_border_width(10)
    window.set_title("Quota Applet")

    ok = gtk.Button("Ok")
    ok.connect_object("clicked", gtk.Widget.destroy, window)
    box = gtk.VBox()

    label = gtk.Label('Quota Notification \n \
Thomas Uphill <uphill at ias dot edu>\n \
Institute for Advanced Study 2011')
    table = gtk.Table(2,1,True)
    table.attach(label,1,2,0,1)
    label.show()
    image = gtk.Image()
    image.set_from_pixbuf(greenPixbuf)
    table.attach(image,0,1,0,1)
    image.show()
    box.pack_start(table)
    table.show()
    box.pack_end(ok)
    ok.show()
    window.add(box)
    box.show()
    window.show()
    
  def quit(self, widget, data = None):
    threading.Thread(target=self.t.shutdown, args=()).start()
    gtk.main_quit()

  def popup_menu_cb(self, widget, button, time, data = None):
    if button == 3:
      if data:
        data.show_all()
        data.popup(None, None, gtk.status_icon_position_menu,
                   3, time, self.statusIcon)

if __name__ == "__main__":
  qn = QuotaNotification()

