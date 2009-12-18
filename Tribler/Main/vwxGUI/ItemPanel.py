# Written by Richard Gwin

import wx, math, time, os, sys, threading
from traceback import print_exc,print_stack

from Tribler.Core.Utilities.utilities import *
from Tribler.Main.vwxGUI.GuiUtility import GUIUtility
from Tribler.Main.vwxGUI.tribler_topButton import tribler_topButton, SwitchButton
from Tribler.Main.vwxGUI.bgPanel import ImagePanel
from Tribler.Core.Utilities.unicode import *
from Tribler.Main.Utility.utility import getMetainfo, similarTorrent, copyTorrent

from Tribler.Core.Utilities.timeouturlopen import urlOpenTimeout
from Tribler.Core.BitTornado.bencode import bencode,bdecode
import urllib
import cStringIO
import string

from copy import deepcopy
import cStringIO
import mimetypes
import tempfile

from font import *
from Tribler.Core.simpledefs import *

from Tribler.Main.vwxGUI.FilesItemDetailsSummary import FilesItemDetailsSummary
from Tribler.Main.vwxGUI.TriblerStyles import TriblerStyles


from Tribler.__init__ import LIBRARYNAME


DEBUG = False

AUTOMODERATION_SAVE_WEBSEARCH_IMAGE_TO_TORRENT = False

# font sizes
if sys.platform == 'darwin':
    FS_FILETITLE = 10
    FS_FILETITLE_SEL = 12 # size of title in expanded torrent
    FS_FILESIZE = 10
    FS_SEEDERS = 10
    FS_LEECHERS = 10
    FS_SIMILARITY = 10
    FS_HEARTRANK = 8
    TITLELENGTH = 80
    TITLEHEIGHT = 18
    TITLEHEIGHTEXP = 18

elif sys.platform == 'linux2':
    FS_FILETITLE = 8
    FS_FILETITLE_SEL = 10 
    FS_FILESIZE = 8
    FS_SEEDERS = 8
    FS_LEECHERS = 8
    FS_SIMILARITY = 7
    FS_HEARTRANK = 7
    TITLELENGTH = 164
    TITLEHEIGHT = 12
    TITLEHEIGHTEXP = 18
else:
    FS_FILETITLE = 8
    FS_FILETITLE_SEL = 10 
    FS_FILESIZE = 8
    FS_SEEDERS = 8
    FS_LEECHERS = 8
    FS_SIMILARITY = 10
    FS_HEARTRANK = 7
    TITLELENGTH = 80
    TITLEHEIGHT = 18
    TITLEHEIGHTEXP = 18


filesModeThumbSize = (125, 70)
#filesModeThumbSizeList = (32, 18)
libraryModeThumbSize = (32,18)#(43,24)#(66, 37)


class ItemPanel(wx.Panel): # can be a torrent item or a channel item
    """
    This Panel shows one content item inside the GridPanel
    """
    def __init__(self, parent, keyfun, name='regular'):
        
        wx.Panel.__init__(self, parent, -1)
        self.guiUtility = GUIUtility.getInstance()
        self.utility = self.guiUtility.utility
        self.session = self.utility.session
        self.parent = parent
        self.data = None
        self.datacopy = {}
        self.titleLength = TITLELENGTH # num characters
        self.triblerGrey = wx.Colour(200,200,200)
        self.selected = False
        self.warningMode = False
        self.summary = None
        self.oldCategoryLabel = None
        self.guiserver = parent.guiserver

        self.guiImagePath = os.path.join(self.guiUtility.utility.getPath(),LIBRARYNAME , 'Main', 'vwxGUI', 'images')
        
        if self.parent.GetName() == 'filesGrid':
            self.listItem = (self.parent.viewmode == 'list')
            self.guiserver = parent.guiserver
        else:
            self.listItem = True
            self.guiserver = GUIServer.getInstance()


        self.channelcast_db = self.session.open_dbhandler(NTFY_CHANNELCAST)
        self.vcdb = self.session.open_dbhandler(NTFY_VOTECAST)
        self.torrent_db = self.session.open_dbhandler(NTFY_TORRENTS)

        self.w1 = 415
        self.w2 = 99
        self.w3 = 80
        self.w4 = 67

        self.h1 = TITLEHEIGHT



        self.addComponents()
        self.Show()
        self.Refresh()
        self.Layout()
        self.gridKeyTyped = keyfun

        self.type = 'torrent' # channel or torrent

        # subscription state
        self.subscribed = False
        
        self.name = name
        self.ThumbnailViewer = ThumbnailViewer
        self.guiUtility.thumbnailViewer = ThumbnailViewer


        

    def addComponents(self):
        
        self.Show(False)
        self.triblerStyles = TriblerStyles.getInstance()

        self.selectedColour = wx.Colour(255,200,187)       
        self.unselectedColour = wx.WHITE
        
        self.SetBackgroundColour(self.unselectedColour)
       
        self.Bind(wx.EVT_MOUSE_EVENTS, self.mouseAction)
        
        
        self.SetMinSize((660,22))

        self.vSizerOverall = wx.BoxSizer(wx.VERTICAL)

        # line
        imgpath = os.path.join(self.utility.getPath(),LIBRARYNAME ,"Main","vwxGUI","images","5.0","line3.png")
        self.line_file = wx.Image(imgpath, wx.BITMAP_TYPE_ANY)            
        self.hLine = wx.StaticBitmap(self, -1, wx.BitmapFromImage(self.line_file))


        self.vSizerOverall.Add(self.hLine, 0, 0, 0)

        self.hSizer = wx.BoxSizer(wx.HORIZONTAL)
            
            

        self.hSizer.Add([10,5],0,wx.FIXED_MINSIZE,0)
        self.vSizerOverall.Add(self.hSizer, 0, wx.EXPAND, 0)

        #self.thumb = ThumbnailViewer(self, 'filesMode')
        #self.thumb.setBackground(wx.BLACK)
        #self.thumb.SetSize((32,18))
        #self.hSizer.Add(self.thumb, 0, wx.ALL, 2)  

        # Add title
        self.title =wx.StaticText(self,-1,"",wx.Point(0,0),wx.Size(300,self.h1))        
        self.title.SetBackgroundColour(wx.WHITE)
        self.title.SetForegroundColour(wx.BLACK)
        self.title.SetFont(wx.Font(FS_FILETITLE,FONTFAMILY,FONTWEIGHT,wx.NORMAL,False,FONTFACE))
        self.title.SetMinSize((300,self.h1))
        self.title.SetSize((300,self.h1))

        self.hSizer.Add(self.title, 0,wx.TOP|wx.BOTTOM, 3)  
  
        self.hSizer.Add([5,0],0 ,0 ,0)



        self.fileSize = wx.StaticText(self,-1,"",wx.Point(0,0),wx.Size(self.w2-5,18), wx.ALIGN_LEFT | wx.ST_NO_AUTORESIZE)        
        self.fileSize.SetBackgroundColour(wx.WHITE)
        self.fileSize.SetForegroundColour(wx.BLACK) 
        self.fileSize.SetFont(wx.Font(FS_FILESIZE,FONTFAMILY,FONTWEIGHT,wx.NORMAL,False,FONTFACE))
        self.fileSize.SetMinSize((self.w2-5,18))

        self.hSizer.Add(self.fileSize, 0,wx.TOP|wx.BOTTOM, 2)  

        self.hSizer.Add([5,0],0 ,0 ,0)


        # seeders
        self.seeders = wx.StaticText(self, -1, "", wx.Point(0,0), wx.Size(self.w3-5,18))
        self.seeders.SetBackgroundColour(wx.WHITE)
        self.seeders.SetForegroundColour(wx.BLACK) 
        self.seeders.SetFont(wx.Font(FS_SEEDERS,FONTFAMILY,FONTWEIGHT,wx.NORMAL,False,FONTFACE))
        self.seeders.SetMinSize((self.w3-5,18))


        # leechers
        self.leechers = wx.StaticText(self, -1, "", wx.Point(0,0), wx.Size(self.w4-5,18))
        self.leechers.SetBackgroundColour(wx.WHITE)
        self.leechers.SetForegroundColour(wx.BLACK) 
        self.leechers.SetFont(wx.Font(FS_LEECHERS,FONTFAMILY,FONTWEIGHT,wx.NORMAL,False,FONTFACE))
        self.leechers.SetMinSize((self.w4-5,18))

        self.hSizer.Add(self.seeders, 0,wx.TOP|wx.BOTTOM, 2)  

        self.hSizer.Add([5,0],0 ,0 ,0)

        self.hSizer.Add(self.leechers, 0,wx.TOP|wx.BOTTOM, 2)  


        self.hSizerSummary = wx.BoxSizer(wx.HORIZONTAL) ##
        self.vSizerOverall.Add(self.hSizerSummary, 0, wx.FIXED_MINSIZE|wx.EXPAND, 0) ##           
 
        if sys.platform != 'linux2':
            self.title.Bind(wx.EVT_MOUSE_EVENTS, self.mouseAction)
            self.fileSize.Bind(wx.EVT_MOUSE_EVENTS, self.mouseAction)
            self.seeders.Bind(wx.EVT_MOUSE_EVENTS, self.mouseAction)
            self.leechers.Bind(wx.EVT_MOUSE_EVENTS, self.mouseAction)


           
        self.SetSizer(self.vSizerOverall); ## self.hSizer
            
        self.SetAutoLayout(1);
        self.Layout();
        self.Refresh()
        
        # 2.8.4.2 return value of GetChildren changed
        wl = []
        for c in self.GetChildren():
            wl.append(c)
        for window in wl:
            window.Bind(wx.EVT_LEFT_UP, self.mouseAction)
            window.Bind(wx.EVT_KEY_UP, self.keyTyped)
#            window.Bind(wx.EVT_LEFT_DCLICK, self.doubleClicked)
#            window.Bind(wx.EVT_RIGHT_DOWN, self.mouseAction)            
            #window.Bind(wx.EVT_RIGHT_DOWN, self.rightMouseButton)  
            
    def getColumns(self):
        return [{'sort':'name', 'reverse':True, 'title':'Name', 'width':self.w1,'tip':self.utility.lang.get('C_filename')},
                {'sort':'length', 'title':'Size', 'width':self.w2, 'tip':self.utility.lang.get('C_filesize')},
                {'sort':'length', 'title':'Seeders', 'width':self.w3, 'tip':self.utility.lang.get('C_uploaders')},
                {'sort':'length', 'title':'Leechers', 'width':self.w4, 'tip':self.utility.lang.get('C_downloaders')},
                ]

    def setType(self, type):
        if type not in ('torrent', 'channel'):
            return
        self.type = type


    def setSubscriptionState(self):
        if self.vcdb.hasVote(self.data['permid'], self.utility.session.get_permid()):
            self.subscribed = True
        else:
            self.subscribed = False




                 
    def setData(self, data):
        
        self.data = data
        
        if not data:
            data = {}

        #self.thumb.Hide() ## should not be shown


        if self.type == 'torrent':
            if data.get('name'):
                titlefull = data['name']
                title = data['name'][:self.titleLength]
                if sys.platform == 'win32':
                    title = string.replace(title,'&','&&')
                #print >> sys.stderr , title
                #print >> sys.stderr , title_new
                self.title.Enable(True)
                self.title.Show()
                self.title.SetLabel(title)
                if sys.platform != 'win32': # on windows causes a new line bug when title contains & symbol
                    self.title.Wrap(self.title.GetSize()[0])
                self.title.SetToolTipString(titlefull)
               


                if self.listItem:
                    self.fileSize.Enable(True)
                    if data.get('web2'):
                        self.fileSize.SetLabel('%s s' % data['length'])
                    else:
                        self.fileSize.SetLabel(self.utility.size_format(data['length']))

                    if data['num_seeders'] < 0:
                        self.seeders.SetForegroundColour((200, 200, 200))
                        self.seeders.SetLabel("?")                
                    else:
                        self.seeders.SetForegroundColour(wx.BLACK)
                        self.seeders.SetLabel("%s " % data['num_seeders'])                

                    if data['num_leechers'] < 0:
                        self.leechers.SetForegroundColour((200, 200, 200))
                        self.leechers.SetLabel("?")                
                    else:
                        self.leechers.SetForegroundColour(wx.BLACK)
                        self.leechers.SetLabel("%s " % data['num_leechers'])                

   
                    self.hLine.Show()

                
                
            else:
                self.title.SetLabel('')
                self.title.SetToolTipString('')
                self.title.Enable(False)
                self.title.Hide()
                self.seeders.SetLabel('')                
                self.leechers.SetLabel('')                
                if self.listItem:
                    # -- if list VIEW --
                    self.fileSize.SetLabel('')
 

            
        else: # channel
           
            if data.get('name'):
                title = data['name'][:self.titleLength]
                if sys.platform == 'win32':
                    title = string.replace(title,'&','&&')
                self.title.Enable(True)
                self.title.SetLabel(title)
                if sys.platform != 'win32': # on windows causes a new line bug when title contains & symbol
                    self.title.Wrap(self.title.GetSize()[0])
                self.title.SetToolTipString(title)


                # determine whether subscribed to channel
                self.setSubscriptionState()


                # get torrent list
                self.torrentList = self.channelcast_db.getTorrentsFromPublisherId(data['permid'])


                # convert torrentList to proper format (dictionnary)
                torrent_list = []
                for item in self.torrentList:
                    torrent = dict(zip(self.torrent_db.value_name_for_channel, item))
                    torrent_list.append(torrent)
                self.torrentList = torrent_list






                if self.listItem:
                    self.fileSize.Enable(True)
                    self.hLine.Show()

                
                
            else:
                self.title.SetLabel('')
                self.title.SetToolTipString('')
                self.title.Enable(False)
                self.fileSize.SetLabel('')
                self.seeders.SetLabel('')
                self.leechers.SetLabel('')
                ##if self.popularity:
                ##    self.popularity.Hide()


        self.Layout()
        

    def addLine(self):
        vLine = wx.StaticLine(self,-1,wx.DefaultPosition, wx.Size(2,22),wx.LI_VERTICAL)
        self.hSizer.Add(vLine, 0, wx.RIGHT|wx.LEFT|wx.EXPAND, 3)
        return vLine
          

    def select(self, rowIndex, colIndex, pageIndex=-1, panelsPerRow=-1, rowsPerPage=-1):
        # if pageIndex is given, we assume panelsPerRow and rowsPerPage are given as well,
        # and set click_position, a 0-indexed value indicating the rank of the panel
        if pageIndex>-1:
             panelsPerPage = panelsPerRow * rowsPerPage
             self.data["click_position"] = pageIndex * panelsPerPage + rowIndex * panelsPerRow + colIndex
        self.selected = True

        if self.data and self.data.get('myDownloadHistory'):
            colour = self.guiUtility.selectedColour
        elif self.data and self.data.get('query_torrent_was_requested',False):
            colour = self.guiUtility.selectedColourPending
        else:
            colour = self.guiUtility.selectedColour

        self.title.SetBackgroundColour(colour)
        self.title.SetFont(wx.Font(FS_FILETITLE_SEL,FONTFAMILY,FONTWEIGHT,wx.BOLD,False,FONTFACE))
        self.title.SetMinSize((self.w1-5, TITLEHEIGHTEXP))
        self.title.SetSize((self.w1-5, TITLEHEIGHTEXP))
        
        
        self.SetBackgroundColour(colour)
        self.fileSize.SetBackgroundColour(colour)
        self.toggleItemDetailsSummary(True)
        if self.type == 'torrent':
            self.guiUtility.standardOverview.selectedTorrent = self.data['infohash']
        else: # channel
            self.guiUtility.standardOverview.selectedChannel = self.data['infohash']
        self.Refresh()
        self.guiUtility.standardOverview.SetFocus()
        
    def deselect(self, rowIndex, colIndex):

        self.selected = False
        self.hLine.Show()
        self.vSizerOverall.Layout()
        downloading = self.data and self.data.get('myDownloadHistory')
        if rowIndex % 2 == 0 or not self.listItem:
            if downloading:
                colour = self.guiUtility.unselectedColour
            else:
                colour = self.guiUtility.unselectedColour
        else:
            if downloading:
                colour = self.guiUtility.unselectedColour2
            else:
                colour = self.guiUtility.unselectedColour2
        
            
        self.title.SetBackgroundColour(colour)
        self.title.SetFont(wx.Font(FS_FILETITLE,FONTFAMILY,FONTWEIGHT,wx.NORMAL,False,FONTFACE))
        self.title.SetMinSize((self.w1-5, TITLEHEIGHT))
        self.title.SetSize((self.w1-5, TITLEHEIGHT))

        self.SetBackgroundColour(colour)
        self.fileSize.SetBackgroundColour(colour)
        self.seeders.SetBackgroundColour(colour)
        self.leechers.SetBackgroundColour(colour)
       
        self.toggleItemDetailsSummary(False)
        self.Refresh()
        
    def keyTyped(self, event):
        if self.selected:
            key = event.GetKeyCode()
            if (key == wx.WXK_DELETE):
                if self.data:
                    if DEBUG:
                        print >>sys.stderr,'fip: deleting'
                    #self.guiUtility.deleteTorrent(self.data)
        event.Skip()
        try:
            self.gridKeyTyped(event)
        except:
            print 'Exception in keytyped'
            
    def popularityOver(self, event):
        
        event.Skip()
        colour = wx.Colour(216,233,240)

        if self.data is None:
            colour = self.guiUtility.unselectedColour

        elif event.Entering() and self.data is not None:
            colour = self.guiUtility.selectedColour
    


        self.title.SetBackgroundColour(colour)
        self.fileSize.SetBackgroundColour(colour)
        self.SetBackgroundColour(colour)
        wx.CallAfter(self.Refresh)


        if self.data and (event.LeftUp() or event.RightDown()):
            # torrent data is sent to guiUtility > standardDetails.setData
            self.guiUtility.selectTorrent(self.data)
            
    def setIndex(self, index):
        self.index=index


            
        
    def mouseAction(self, event):   

        event.Skip()
        colour = wx.Colour(216,233,240)

        if self.data is None:
            colour = self.guiUtility.unselectedColour

        elif event.Entering() and self.data is not None:
            colour = self.guiUtility.selectedColour
    
        elif event.Leaving() and self.selected == False:
            colour = self.guiUtility.unselectedColour


        self.title.SetBackgroundColour(colour)
        self.fileSize.SetBackgroundColour(colour)
        self.seeders.SetBackgroundColour(colour)
        self.leechers.SetBackgroundColour(colour)
        self.SetBackgroundColour(colour)
        wx.CallAfter(self.Refresh)


        if self.data and (event.LeftUp() or event.RightDown()):
            self.guiUtility.selectTorrent(self.data)

           

    def rightMouseButton(self, event):       
        menu = self.guiUtility.OnRightMouseAction(event)
        if menu is not None:
            self.PopupMenu(menu, (-1,-1)) 

    def doubleClicked(self, event):
        self.guiUtility.standardDetails.download(self.data)
        
    def getIdentifier(self):
        return self.data['infohash']


    def toggleItemDetailsSummary(self, visible):
        if visible and not self.summary:            
            if not self.data.get('web2'):                
                self.guiUtility.moderatedinfohash = self.data['infohash']
                self.summary = FilesItemDetailsSummary(self, torrentHash = self.data['infohash'], torrent = self.data)
            else:
                self.summary = FilesItemDetailsSummary(self, torrentHash = None, torrent = self.data, web2data = self.data)
            self.hSizerSummary.Add(self.summary, 1, wx.ALL|wx.EXPAND, 0)
            if sys.platform == 'win32':
                self.SetMinSize((-1,97))
            elif sys.platform == 'darwin':
                self.SetMinSize((-1,101))
            else:
                self.SetMinSize((-1,100))                
        elif visible and self.summary:
            pass
   
        elif self.summary and not visible:
            self.summary.Hide()
            wx.CallAfter(self.summary.DestroyChildren)
            wx.CallAfter(self.summary.Destroy)
            self.summary = None
            self.SetMinSize((-1,22))               



class ThumbnailViewer(wx.Panel):
    """
    Show thumbnail and mast with info on mouseOver
    """

    def __init__(self, parent, mode, **kw):
        self.parent = parent 
        wx.Panel.__init__(self, parent, **kw)
        self.mode = mode
        self._PostInit()
        
    def OnCreate(self, event):
        self.Unbind(wx.EVT_WINDOW_CREATE)
        wx.CallAfter(self._PostInit)
        event.Skip()
        return True
    
    def _PostInit(self):
        # Do all init here
        self.backgroundColor = wx.WHITE
        self.torrentBitmap = None
        self.torrent = None
        self.mouseOver = False
        self.triblerGrey = wx.Colour(128,128,128)
        self.triblerLightGrey = wx.Colour(203,203,203)
        self.sourceIcon = None  
        self.guiUtility = GUIUtility.getInstance()
        self.Bind(wx.EVT_MOUSE_EVENTS, self.mouseAction)
        self.Bind(wx.EVT_LEFT_UP, self.guiUtility.buttonClicked)
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnErase)
        self.selected = False
        self.border = None
        self.downloading = False
        self.categoryIcon = None

    
    def setTorrent(self, torrent):
        if not torrent:
            self.Hide()
            self.Refresh()
            return
        
        if not self.IsShown():
            self.Hide() ## self.Show()
       

        self.torrent = torrent
        ##self.setThumbnail(torrent)
        ##self.setCategoryIcon(torrent)
        # items in library should not show downloading color
        self.downloading = torrent.get('myDownloadHistory', False) and self.mode != 'libraryMode'
        
                            
    def setCategoryIcon(self, torrent):
        
        #print >>sys.stderr,"fip: ",`torrent['name']`,"has cat",torrent.get('category')
        self.categoryIcon = self.iconsManager.getCategoryIcon(self.mode, torrent.get('category'), thumbtype='icon', web2 = torrent.get('web2'))
    
    def setSourceIcon(self, si):
        self.sourceIcon = si
        
    def setThumbnail(self, torrent):
        #print >>sys.stderr,"fip: setThumb:",torrent['name']
        
        thumbtype = (self.parent.listItem) and 'small' or 'normal'
        bmp = None
        readable = torrent.get('metadata',{}).get('ThumbReadable')
        if readable == False:
            bmp = self.iconsManager.getCategoryIcon(self.mode,torrent.get('category'), thumbtype=thumbtype, web2 = torrent.get('web2'))
        
        else:        
            # Check if we have already read the thumbnail and metadata information from this torrent file
            if 'preview' in torrent:
                self.GetParent().guiserver.add_task(lambda:self.loadMetadata(torrent,None),0)
                
            elif torrent.get('metadata',{}).get('ThumbnailBitmap'):
                if self.mode == 'libraryMode' or self.parent.listItem:
                    # Make a resized thumb for lib view
                    bmp = torrent['metadata'].get('ThumbnailBitmap')
                    if bmp:
                        img = bmp.ConvertToImage()
                        bmp = getResizedBitmapFromImage(img, libraryModeThumbSize)
                        
                elif self.mode == 'filesMode':
                    bmp = torrent['metadata'].get('ThumbnailBitmap')
            elif 'torrent_file_name' in torrent and torrent['torrent_file_name'] != '':
                torrent_dir = self.guiUtility.utility.session.get_torrent_collecting_dir()
                torrent_filename = os.path.join(torrent_dir, torrent['torrent_file_name'])
                
                if DEBUG:
                    print "fip: Scheduling read of thumbnail for",`torrent['name']`,"from",torrent_filename
                
                def loadMetaDataNow():
                    try:
                        self.loadMetadata(torrent,torrent_filename)
                    except wx.PyDeadObjectError:
                        pass
                    
                try:
                    self.GetParent().guiserver.add_task(loadMetaDataNow,0)
                except wx.PyDeadObjectError:
                    pass
        
                # ARNO: TODO: The FileItemPanels that use this ThumbnailViewer now get deleted, and thus
                # also the ThumbnailViewer objects. Or at least the C++ part of them. As a result we
                # can no longer schedule these loadMetadata callbacks on the GUITaskQueue thread. 
                #
                # At the moment, the wx code protects us, and throws an exception that the C++ part
                # of the ThumbnailViewer object is gone. But we should clean this up. 
            
        if not bmp:
            bmp = self.iconsManager.getCategoryIcon(self.mode, torrent.get('category'), thumbtype=thumbtype, web2 = torrent.get('web2'))
        
        assert bmp, 'No bitmap found for %s' % `torrent['name']`
        self.setBitmap(bmp)
        width, height = self.GetSize()
        d = 1
        self.border = [wx.Point(0,d), wx.Point(width-d, d), wx.Point(width-d, height-d), wx.Point(d,height-d), wx.Point(d,0)]
        self.Refresh()
        #wx.Yield()
        
        
         
    def setBitmap(self, bmp):
        # Recalculate image placement
        if not bmp:
            self.torrentBitmap = None
            self.xpos, self.ypos = 0,0
            raise Exception('Warning: Thumbnail set to None for %s' % `self.torrent`)
        else:
            w, h = self.GetSize()
            iw, ih = bmp.GetSize()
                    
            self.torrentBitmap = bmp
            self.xpos, self.ypos = (w-iw)/2, (h-ih)/2
        
        
    def loadMetadata(self, torrent,torrent_filename):
        """ Called by separate non-GUI thread """
        
        if DEBUG:
            print >>sys.stderr,"fip: ThumbnailViewer: loadMetadata",torrent_filename
        if not torrent.get('preview'):
            if not os.path.exists(torrent_filename):
                if DEBUG:    
                    print >>sys.stderr,"fip: ThumbnailViewer: loadMetadata: %s does not exist" % torrent_filename
                return None

            # We can't do any wx stuff here apparently, so the only thing we can do is to
            # read the data from the torrent file and create the wxBitmap in the GUI callback.

            newmetadata = loadAzureusMetadataFromTorrent(torrent_filename)
            
            
            if newmetadata.get('Thumbnail') is None and AUTOMODERATION_SAVE_WEBSEARCH_IMAGE_TO_TORRENT:
                # Use Google Image search to find a thumb
                (mimetype,thumbdata) = google_image_search(torrent['name'])
                
                if DEBUG:
                    if thumbdata is None:
                        t = None
                    else:
                        t = 'data'
                    print >>sys.stderr,"fip: automod: Google Image Search Got:",mimetype,t
                
                if mimetype is not None and thumbdata is not None:
                    # Scale image
                    scaledthumbdata = scale_image_convert_jpeg(mimetype,thumbdata,171)
                    newmetadata = { 'Thumbnail' : scaledthumbdata}
                    
                    # Save thumb data in torrent, auto-moderation ;o)
                    saveAzureusMetadataToTorrent(torrent_filename,scaledthumbdata)
        else:
            # Web2 items have preview fields
            newmetadata = { 'Thumbnail' : torrent['preview'] }

      
        wx.CallAfter(self.metadata_thread_gui_callback,torrent,newmetadata)

             
    def metadata_thread_gui_callback(self,torrent,metadata):
        """ Called by GUI thread """

        #print 'Azureus_thumb: %s' % thumbnailString
        thumbnailString = metadata.get('Thumbnail')
         
        if thumbnailString:
            #print 'Found thumbnail: %s' % thumbnailString
            
            img = createThumbImage(thumbnailString)
            if img is None:
                return           

            bmp = getResizedBitmapFromImage(img, filesModeThumbSize)
            
            if bmp:
                metadata['ThumbnailBitmap'] = bmp
                metadata['ThumbnailReadable'] = True
            ## We now scale live
            #bmplib = getResizedBitmapFromImage(img, libraryModeThumbSize)
            #if bmplib:
            #    metadata['ThumbnailBitmapLibrary'] = bmplib
                
            # Dump the raw data
            #del metadata['Thumbnail']
        else:
            metadata['ThumbnailReadable'] = False
          
        torrent['metadata'] = metadata
        
        # This item may be displaying another torrent right now, only show the icon
        # when it's still the same torrent
        
        #print >>sys.stderr,"fip: meta_gui_cb: old torrent",`torrent['name']`,"new torrent",`self.torrent['name']`
        #print >>sys.stderr,"fip: meta_gui_cb: old torrent",`torrent['infohash']`,"new torrent",`self.torrent['infohash']`
        try:
            if torrent['infohash'] == self.torrent['infohash']:
                bmp = metadata.get('ThumbnailBitmap')
                if bmp:
                    if self.parent.listItem:
                        bmp = getResizedBitmapFromImage(img, libraryModeThumbSize)
                    self.setBitmap(bmp)
                    self.Refresh()
        except wx.PyDeadObjectError:
            pass
             
    
            
    def OnErase(self, event):
        pass
        #event.Skip()
        
    def setSelected(self, sel):
        self.selected = sel
        self.Refresh()
        
    def isSelected(self):
        return self.selected
        
    def mouseAction(self, event):
        if event.Entering():
            #print 'enter' 
            self.mouseOver = True
            self.Refresh()
        elif event.Leaving():
            self.mouseOver = False
            #print 'leave'
            self.Refresh()
        
        """
    def ClickedButton(self):
        print 'Click'
        """
                
    def setBackground(self, wxColor):
        self.backgroundColor = wxColor
        
    def OnPaint(self, evt):
        dc = wx.BufferedPaintDC(self)
        dc.SetBackground(wx.Brush(self.backgroundColor))
        dc.Clear()
        

        if self.torrent and self.mode == 'filesMode':
            rank = self.torrent.get('simRank', -1)
        else:
            rank = -1
            
        heartBitmap = TasteHeart.getHeartBitmap(rank)
        
        
        if self.torrentBitmap:
            dc.DrawBitmap(self.torrentBitmap, self.xpos,self.ypos, True)
#            dc.SetFont(wx.Font(6, wx.SWISS, wx.NORMAL, wx.BOLD, True))
#            dc.DrawBitmap(MASK_BITMAP,0 ,52, True)
#            dc.SetTextForeground(wx.BLACK)
            #dc.DrawText('rating', 8, 50)

        if self.categoryIcon:
            dc.DrawBitmap(self.categoryIcon, 99, 7, True)      
        if self.sourceIcon:
            dc.DrawBitmap(self.sourceIcon, 101, 27, True)
            
        if self.mouseOver:
            dc.SetFont(wx.Font(6, FONTFAMILY,FONTWEIGHT, wx.BOLD, True, FONTFACE))
            mask = self.iconsManager.get_default('filesMode','MASK_BITMAP')
            dc.DrawBitmap(mask,0 ,0, True)
        
        if heartBitmap:
            mask = self.iconsManager.get_default('filesMode','MASK_BITMAP_BOTTOM')
            margin = 52
            dc.DrawBitmap(mask,0 ,margin, True)
            dc.DrawBitmap(heartBitmap,5 ,margin+2, True)
            dc.SetFont(wx.Font(FS_HEARTRANK, FONTFAMILY, FONTWEIGHT, wx.BOLD, False, FONTFACE))
            text = repr(rank)                
            dc.DrawText(text, 22, margin+4)
        
            
        if self.border:
            if self.selected:
                if self.downloading:
                    colour = self.guiUtility.selectedColourDownload
                else:
                    colour = self.guiUtility.triblerRed
            else:
                if self.downloading:
                    colour = self.guiUtility.unselectedColourDownload
                else:
                    colour = self.triblerLightGrey
            dc.SetPen(wx.Pen(colour, 2))
            dc.DrawLines(self.border)


def loadAzureusMetadataFromTorrent(torrent_filename):
    metadata = getMetainfo(torrent_filename)
    if not metadata:
        return None
            
    newmetadata = metadata.get('azureus_properties', {}).get('Content',{})
    for key in ['encoding','comment','comment-utf8']: # 'created by'
        if key in metadata:
            newmetadata[key] = metadata[key]
    return newmetadata


def createThumbImage(imgdata):
    try:
        # Simple protection against bad parsing of websites, if the
        # image data is HTML, ignore it.
        
        low = imgdata[:5].lower()
        if low == '<html' or low == '<!doc':
            return None
    except:
        #print_exc()
        pass
    
    stream = cStringIO.StringIO(imgdata)
    img =  wx.ImageFromStream(stream)
    if not img.Ok():
        return None
    return img

def getResizedBitmapFromImage(img, size):
        "Resize image to size of self"
        iw, ih = img.GetSize()
        w, h = size

        if iw == 0 or ih == 0:
            # Can happen when there is no handler for image type
            return None
        
        if (iw/float(ih)) > (w/float(h)):
            nw = w
            nh = int(ih * w/float(iw))
        else:
            nh = h
            nw = int(iw * h/float(ih))
        if nw != iw or nh != ih:
            #print 'Rescale from (%d, %d) to (%d, %d)' % (iw, ih, nw, nh)
            img.Rescale(nw, nh)
        bmp = wx.BitmapFromImage(img)
        return bmp

def google_image_search(name):
    try:
        rname = name.replace('.',' ')
        rname = rname.replace('-',' ')
        rname = rname.replace('_',' ')
        rname = rname.replace('[',' ')
        rname = rname.replace(']',' ')
        if DEBUG:
            print >>sys.stderr,"fip: automod: Name becomes keywords",rname
        
        qname = urllib.quote(rname)

        # 1. Query Google Image search
        url = 'http://www.searchmash.com/results/images:'+qname+''
        if DEBUG:
            print >>sys.stderr,"fip: automod: Query URL",url
        f = urlOpenTimeout(url,timeout=2)
        resp = f.read()
        f.close()
        
        start = 0
        while True:
            #print >>sys.stderr,"fip: automod: Searching from idx",start
            i = resp.find("imageUrl",start)
            if i == -1:
                break
            else:
                i += len("imageUrl\":\"")
                j = resp.find("\"",i)
                if j == -1:
                    break
                else:
                    # 2. Found an Image, see if we can guess MIME type
                    imgurl = resp[i:j]
                    if DEBUG:
                        print >>sys.stderr,"fip: automod: Found image",imgurl

                    iconmime = mimetypes.guess_type(imgurl)[0]
                    if iconmime is None:
                        start = j
                        continue
                    
                    # 3. Load the image
                    try:
                        f = urlOpenTimeout(imgurl,timeout=2)
                        imgresp = f.read()
                        f.close()
                        
                        if imgresp == '':
                            start = j
                            continue
                        
                        return (iconmime,imgresp)
                    except:
                        print_exc()
                        start = j
                        continue
    except:
        print_exc()
    return (None,None)


def scale_image_convert_jpeg(mimetype,data,dim):
    icondata = None
    try:
        cio = cStringIO.StringIO(data)
        if wx.Image.CanReadStream(cio):
            sim = data2wxImage(mimetype,data,dim=dim)
            [thumbhandle,thumbfilename] = tempfile.mkstemp("torrent-thumb")
            os.close(thumbhandle)
            sim.SaveFile(thumbfilename,wx.BITMAP_TYPE_JPEG)
                            
            f = open(thumbfilename,"rb")
            icondata = f.read()
            f.close()
            
            os.remove(thumbfilename)
    except:
        print_exc()
        
    return icondata
    

def saveAzureusMetadataToTorrent(torrentfilename,scaledthumbdata):
    try:
        f = open(torrentfilename,"rb")
        data = f.read()
        f.close()
        d = bdecode(data)
        
        d['azureus_properties'] = {}
        d['azureus_properties']['Content'] = {}
        d['azureus_properties']['Content']['Thumbnail'] = scaledthumbdata
        
        newdata = bencode(d)
        f = open(torrentfilename,"wb")
        f.write(newdata)
        f.close()
    except:
        print_exc()
        
