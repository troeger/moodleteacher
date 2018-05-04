import os
import sys
import subprocess
import tempfile

import wx 
import wx.html2 
import wx.lib.sized_controls as sc
from wx.lib.pdfviewer import pdfViewer, pdfButtonPanel

class Viewer(sc.SizedFrame):
    def __init__(self, **kwargs):
        super().__init__(parent=None, **kwargs)
        self.init_key_event_handlers()

    def init_key_event_handlers(self):
        randomId = wx.NewId()
        self.Bind(wx.EVT_MENU, self.OnClose, id=randomId)
        accel_tbl = wx.AcceleratorTable([(wx.ACCEL_CTRL,  ord('Q'), randomId )])
        self.SetAcceleratorTable(accel_tbl)
  
    def OnClose(self, event):
        self.Destroy()


class PDFViewer(Viewer):
    def __init__(self, title=None, file_name=None, **kwargs):
        super().__init__(**kwargs)

        paneCont = self.GetContentsPane()
        self.buttonpanel = pdfButtonPanel(paneCont, wx.NewId(),
                                wx.DefaultPosition, wx.DefaultSize, 0)
        self.buttonpanel.SetSizerProps(expand=True)
        self.viewer = pdfViewer(paneCont, wx.NewId(), wx.DefaultPosition,
                                wx.DefaultSize,
                                wx.HSCROLL|wx.VSCROLL|wx.SUNKEN_BORDER)

        self.viewer.SetSizerProps(expand=True, proportion=1)

        # introduce buttonpanel and viewer to each other
        self.buttonpanel.viewer = self.viewer
        self.viewer.buttonpanel = self.buttonpanel
        self.viewer.LoadFile(file_name)

class HTMLViewer(Viewer): 
    def __init__(self, title=None, html_text=None, **kwargs):
        super().__init__(**kwargs) 
        sizer = wx.BoxSizer(wx.VERTICAL) 
        m_text = wx.StaticText(self, -1, title)
        sizer.Add(m_text)
    
        self.browser = wx.html2.WebView.New(self) 
        self.browser.SetPage(html_text,"") 
        sizer.Add(self.browser, wx.ID_ANY, wx.EXPAND | wx.ALL, 20) 
        self.SetSizer(sizer) 
        self.SetSize((700, 700)) 
  

def show_html_preview(title, text):
    '''
        Show HTML preview.

        wxPython relies on a rendering backend from an installed browser.
    '''
    app = wx.App() 
    dialog = HTMLViewer(title, text) 
    dialog.Show() 
    app.MainLoop() 

def show_pdf_preview(title, byte_data):
    '''
        Show PDF preview.

        Instead of the buggy wxPython PDF viewer, we could simply
        rely on the operating system to open the file (os.startfile).
        The problem is the synchronous waiting for this application to end,
        so that the temp file is not deleted too early.
    '''
    with tempfile.NamedTemporaryFile() as disk_file:
        disk_file.write(byte_data)
        disk_file.flush()
        app = wx.App() 
        dialog = PDFViewer(title, disk_file.name, size=(800, 600))
        dialog.Show()
        app.MainLoop()

def show_file_preview(title, moodle_submission_file):
    if moodle_submission_file.content_type in moodle_submission_file.UNKNOWN_CONTENT:
        return False
    if moodle_submission_file.is_pdf:
        show_pdf_preview(title, moodle_submission_file.content)
    else:
        show_html_preview(title, "<pre>"+moodle_submission_file.content+"</pre>")
    return True