import os
import sys
import subprocess
import tempfile
import mimetypes
import html
import io
from zipfile import ZipFile
from io import BytesIO

import wx 
import wx.html2 
import wx.lib.sized_controls as sc
from wx.lib.pdfviewer import pdfViewer, pdfButtonPanel
import wx.lib.agw.flatnotebook as fnb

from . import MoodleSubmissionFile

class Viewer(sc.SizedFrame):
    def __init__(self, **kwargs):
        super().__init__(parent=None, **kwargs)
        self.init_key_event_handlers()
        self.SetSize((800, 600)) 

    def init_key_event_handlers(self):
        randomId = wx.NewId()
        self.Bind(wx.EVT_MENU, self.OnClose, id=randomId)
        accel_tbl = wx.AcceleratorTable([(wx.ACCEL_CTRL,  ord('Q'), randomId )])
        self.SetAcceleratorTable(accel_tbl)
  
    def OnClose(self, event):
        self.Destroy()

class HtmlTab(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.viewer = wx.html2.WebView.New(self) 
        vsizer = wx.BoxSizer(wx.HORIZONTAL)
        vsizer.Add(self.viewer, flag=wx.EXPAND|wx.TOP|wx.ALL, border=8, proportion=1)
        self.SetSizer(vsizer)

    def update(self, html_text):
        self.viewer.SetPage(html_text,"") 
     
class PdfTab(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        vsizer = wx.BoxSizer(wx.VERTICAL)

        self.buttonpanel = pdfButtonPanel(self, wx.NewId(),
                                wx.DefaultPosition, wx.DefaultSize, 0)
        vsizer.Add(self.buttonpanel, flag=wx.TOP|wx.ALL, border=8, proportion=0)

        self.viewer = pdfViewer(self, wx.NewId(), wx.DefaultPosition,
                                wx.DefaultSize,
                                wx.HSCROLL|wx.VSCROLL|wx.SUNKEN_BORDER)
        vsizer.Add(self.viewer, flag=wx.EXPAND|wx.BOTTOM|wx.ALL, border=8, proportion=1)

        # introduce buttonpanel and viewer to each other
        self.buttonpanel.viewer = self.viewer
        self.viewer.buttonpanel = self.buttonpanel

        self.SetSizer(vsizer)

        self.pdf_file = tempfile.NamedTemporaryFile()

    def update(self, pdf_data):
        self.pdf_file.seek(0)
        self.pdf_file.write(pdf_data)
        self.pdf_file.flush()
        self.viewer.LoadFile(self.pdf_file)

class ImageTab(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.image = wx.EmptyImage(240,240)
        self.image_ctrl = wx.StaticBitmap(self, wx.ID_ANY, wx.BitmapFromImage(self.image))
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.image_ctrl, flag=wx.EXPAND|wx.TOP|wx.ALL, border=8, proportion=1)
        self.SetSizer(sizer)

    def update(self, image_data):
        sbuf = io.BytesIO(image_data)
        self.image = wx.ImageFromStream(sbuf)
# Perform on window resize, too
#        W,H = self.GetSize()
#        self.image.Rescale(W,H)
        self.image_ctrl.SetBitmap(wx.BitmapFromImage(self.image))
        self.Refresh() 

class MultiFileViewer(Viewer):
    def __init__(self, title, files):
        super().__init__() 

        font = wx.SystemSettings.GetFont(wx.SYS_SYSTEM_FONT)
        font.SetPointSize(9)

        vsizer = wx.BoxSizer(wx.VERTICAL)

        m_text = wx.StaticText(self, -1, title)
        vsizer.Add(m_text)

        info_sizer = wx.BoxSizer(wx.HORIZONTAL)
        entry_list = wx.ListBox(self)
        info_sizer.Add(entry_list, 1, flag=wx.EXPAND|wx.LEFT)

        self.nb = fnb.FlatNotebook(self)
        self.nb.HideTabs()
        self.html_tab = HtmlTab(self.nb)
        self.pdf_tab = PdfTab(self.nb)
        self.image_tab = ImageTab(self.nb)
        self.nb.AddPage(self.html_tab, "HTML Preview")
        self.nb.AddPage(self.pdf_tab, "PDF Preview")
        self.nb.AddPage(self.image_tab, "Image Preview")

        info_sizer.Add(self.nb, 3, flag=wx.EXPAND|wx.RIGHT)
        vsizer.Add(info_sizer, 1, flag=wx.EXPAND|wx.TOP|wx.ALL, border=8)

        self.SetSizer(vsizer)

        for f in files:
            if f.is_zip:
                input_zip=ZipFile(BytesIO(f.content))
                arch_files = [info.filename for info in input_zip.infolist() if not info.is_dir()]
                for fname in arch_files:
                    data = input_zip.read(fname)
                    sub_f = MoodleSubmissionFile(filename=fname, content=data, content_type=mimetypes.guess_type(fname)[0])
                    entry_list.Append(fname + " (in ZIP)", clientData=sub_f)
            else:
                entry_list.Append(f.filename, clientData=f)

        entry_list.Bind(wx.EVT_LISTBOX, self.on_event_files_select)
        entry_list.SetSelection(0)
        self.update(entry_list.GetClientData(0))

    def update(self, moodle_file):
        if moodle_file.is_pdf:
            self.pdf_tab.update(moodle_file.content)
            self.nb.SetSelection(1)
        elif moodle_file.is_html:
            self.html_tab.update(moodle_file.content)
            self.nb.SetSelection(0)
        elif moodle_file.is_image:
            self.image_tab.update(moodle_file.content)
            self.nb.SetSelection(2)
        else:
            if moodle_file.content:
                if isinstance(moodle_file.content, str):
                    html_content = "<pre>"+html.escape(moodle_file.content)+"</pre>"
                else:
                    txt = str(moodle_file.content, encoding="utf-8", errors="ignore")
                    html_content = "<pre>"+html.escape(txt)+"</pre>"
            else:
                html_content = ""
            self.html_tab.update(html_content)
            self.nb.SetSelection(0)

    def on_event_files_select(self, event):
        self.update(event.ClientData)

def show_preview(title, files):
    app = wx.App() 
    dialog = MultiFileViewer(title, files) 
    dialog.Show() 
    app.MainLoop() 
