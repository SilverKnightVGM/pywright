import os,sys
if sys.platform=="win32":
    os.environ['SDL_VIDEODRIVER']='windib'
import zlib
from core import pygame
import threading,time,urllib,urllib2
from zipfile import ZipFile,ZIP_DEFLATED
from pwvlib import *

ERROR_STR= """Error removing %(path)s, %(error)s """

def rmgeneric(path, __func__):
    try:
        __func__(path)
        print 'Removed ', path
    except OSError, (errno, strerror):
        print ERROR_STR % {'path' : path, 'error': strerror }
            
def removeall(path):
    if not os.path.isdir(path):
        return
    files=os.listdir(path)
    for x in files:
        fullpath=os.path.join(path, x)
        if os.path.isfile(fullpath):
            f=os.remove
            rmgeneric(fullpath, f)
        elif os.path.isdir(fullpath):
            removeall(fullpath)
            f=os.rmdir
            rmgeneric(fullpath, f)

import md5

from gui import *

def createfiles(dir="port"):
    for f in os.listdir("art/"+dir):
        if f == ".svn": continue
        if not os.path.isdir(f): continue
        myzip = ZipFile("zip_"+dir+"/"+f+".zip","w",ZIP_DEFLATED)
        for sub in os.listdir("art/"+dir+"/"+f):
            if sub == ".svn": continue
            myzip.write("art/"+dir+"/"+f+"/"+sub,sub)
        myzip.close()
        print "wrote","zips/"+f+".zip"
        
def create_path(dir):
    pathfull = ""
    for pathpart in dir.split("/"):
        pathfull+=pathpart+"/"
        if not os.path.exists(pathfull):
            os.mkdir(pathfull)
for required_path in ["art/3d","art/bg","art/ev","art/fg","art/general","art/port","music","games","fonts","sfx"]:
    create_path(required_path)

def mynames(dir="art/port"):
    files = {}
    for file in [x for x in os.listdir(dir) if x != ".svn"]:
        files[file] = get_data_from_folder(dir+"/"+file)
    return files

import cStringIO
iconcache = {}
def load_image(path):
    if path not in iconcache:
        f = urllib2.urlopen("http://pywright.dawnsoft.org/"+path)
        txt = f.read()
        f.close()
        f = cStringIO.StringIO(txt)
        icon = pygame.image.load(f,path)
        iconcache[path] = icon
    return iconcache[path]
        
def names(url):
    print "accessing","http://pywright.dawnsoft.org/"+url
    if 1:#try:
        f = urllib2.urlopen("http://pywright.dawnsoft.org/"+url)
    else:#except:
        print "fail"
        return {}
    lines = eval(f.read())
    f.close()
    files = {}
    for x in lines:
        if x["zipname"] in files:
            if compare_versions(x["version"],files[x["zipname"]]["version"])<0:
                continue
        files[x["zipname"]]=x
    return files

screen = pygame.display.set_mode([400,50])
root = widget()
root.width,root.height = [640,480]

Label = label
label = editbox(None,"Select content type to download:")
label.draw_back=False
root.add_child(label)
label.draw(screen)

list = scrollpane([0,0])
list.rpos[1]=100
list.width,list.height = [400,300]
list.status_box = editbox(None,"")
list.status_box.draw_back = False
list.status_box.draw(screen)
root.add_child(list)

def build_list(dir="art/port",url="zip_port_info",check_folder=None):
    list.children = [list.status_box,list.scbar]
    fnd = 0
    list.status_box.text="Scanning local files..."
    mn = mynames(dir)
    list.status_box.text="Fetching data from server..."
    an = names(url)
    if check_folder:
        d = get_data_from_folder(check_folder)
        mn = {}
        for n in an:
            mn[n] = d
    cases = {"NEW":[],"UPDATED":[],"INSTALLED":[]}
    for n in sorted(an.keys()):
        if n not in mn:
            status = "NEW"
        elif compare_versions(an[n]["version"],mn[n]["version"])>0:
            status = "UPDATED"
        else:
            status = "INSTALLED"
        fnd = 1
        cb = checkbox(an[n].get("title",an[n]["zipname"]))
        cb.name = n
        cb.file = an[n]["zipfile"]
        cb.filename = an[n]["zipname"]
        try:
            image = load_image(an[n]["iconurl"])
        except:
            image = None
        p = pane([0,0])
        p.width,p.height = [300,95]
        p.align = "horiz"
        image_b = button(None,"")
        image_b.background = False
        image_b.border = False
        image_b.click_down_over = cb.click_down_over
        image_b.graphic = image
        p.add_child(image_b)
        stats = pane([0,0])
        stats.width,stats.height = [250,93]
        stats.align = "vert"
        stats.background = False
        stats.border = False
        stats.add_child(cb)
        sline = status 
        if an[n].get("author",""):
            sline += "                    "+"by "+an[n]["author"]
        stats.add_child(Label(sline))
        if an[n].get("version_date",""):
            stats.add_child(Label("ver %s updated on %s"%(cver_s(an[n]["version"]),an[n]["version_date"])))
        if an[n].get("website",""):
            url = an[n]["website"]
            urlb = button(None,url)
            urlb.textcolor = [0,0,255]
            try:
                import webbrowser
                setattr(urlb,url,lambda *args: webbrowser.open(url))
            except ImportError:
                pass
            stats.add_child(urlb)
        p.add_child(stats)
        p.bgcolor = {"NEW":[255,200,200],"UPDATED":[200,255,200],"INSTALLED":[255,255,255]}[status]
        cases[status].append(p)
    for s in ["NEW","UPDATED","INSTALLED"]:
        for n in cases[s]:
            list.add_child(n)
    if not fnd:
        list.status_box.text  = "No "+dir+" are available to download"
    else:
        if dir == ".":
            dir = "updates"
        list.status_box.text = "Download "+dir+"! Click check boxes to select."

class Engine:
    mode = "port"
    quit_threads = 0
    dl_url = "http://pywright.dawnsoft.org/"
    def Download_X(self,mode,path,url,check_folder=None):
        def t():
            self.mode = mode
            self.path = path
            self.url = url
            build_list(path,url,check_folder)
            rpos = root.children[root.start_index].rpos
            root.children[root.start_index] = button(self,"download")
            root.children[root.start_index].rpos = rpos
        threading.Thread(target=t).start()
    def Download_Characters(self):
        self.Download_X("port","art/port","updates3/games.cgi?content_type=port&ver_type=tuple")
    def Download_Backgrounds(self):
        self.Download_X("bg","art/bg","updates3/games.cgi?content_type=bg&ver_type=tuple")
    def Download_Foreground(self):
        self.Download_X("fg","art/fg","updates3/games.cgi?content_type=fg&ver_type=tuple")
    def Download_Games(self):
        self.Download_X("games","games","updates3/games.cgi?content_type=games&ver_type=tuple")
    def Download_Music(self):
        self.Download_X("music","music","updates3/games.cgi?content_type=music&ver_type=tuple")
    def Update_PyWright(self,thread=True):
        self.path = "."
        self.Download_X("engine",".","updates3/games.cgi?content_type=engine&ver_type=tuple",check_folder=".")
    def do_downloads(self,checkfolder=True,output=None):
        print list.children
        for x in list.children[2:]:
            check = x.children[1].children[0]
            if check.checked:
                if os.path.exists("downloads/"+check.filename+"_url"):
                    seek,path,filename,url = open("downloads/"+check.filename+"_url","r").read().split(" ")
                    self.download_file(path,filename,url,output,seek)
                else:
                    self.download_file(self.path,check.filename,self.dl_url+check.file,output)
    def download_file(self,path,filename,url,output=None,seek=0):
        if not hasattr(self,"progress"):
            self.progress = progress()
            root.add_child(self.progress)
        self.progress.height = 20
        self.progress.width = 400
        self.progress.rpos[1] = list.rpos[1]+list.height+20
        self.progress.progress = 0
        headers = {"User-Agent":"pywright downloader"}
        if seek:
            seek = int(seek)
            serv = urllib2.urlopen(url)
            size = int(serv.info()["Content-Length"])
            headers["Range"] = "bytes=%d-%d"%(seek,size)
            serv.close()
        req = urllib2.Request(url,None,headers)
        try:
            serv = urllib2.urlopen(req)
        except:
            seek = 0
            serv = urllib2.urlopen(url)
        size = int(serv.info()["Content-Length"])
        read = seek
        bytes = seek
        prog = open("downloads/"+filename+"_url","w")
        prog.write(str(seek)+" "+path+" "+filename+" "+url)
        prog.close()
        f = open("downloads/last","w")
        f.write(path+" "+filename)
        f.close()
        old = None
        if seek:
            f = open("downloads/"+filename,"rb")
            old = f.read()
            f.close()
        cli = open("downloads/"+filename,"wb")
        if old:
            cli.write(old)
        s = time.time()
        bps = 0
        while not Engine.quit_threads:
            r = serv.read(4096)
            if not r: break
            cli.write(r)
            read += len(r)
            bytes += len(r)
            self.progress.progress = read/float(size)
            if time.time()-s>1:
                bps = bytes/(time.time()-s)
                s = time.time()
                bytes = 0
            self.progress.text = "%sKB/%sKB - %s KB/s"%(read/1000.0,size/1000.0,bps/1000.0)
            if output:
                self.progress.rpos = [0,0]
                self.progress.width = 256
                self.progress.draw(output[0])
                output[1]()
                for evt in pygame.event.get():
                    if evt.type == pygame.QUIT: raise SystemExit
            prog = open("downloads/"+filename+"_url","w")
            prog.write(str(read)+" "+path+" "+filename+" "+url)
            prog.close()
        serv.close()
        cli.close()
        self.extract_zip(path,filename)
        self.progress.text = "FINISHED"
        del self.progress
        if self.mode == "games":
            self.Download_Games()
    def extract_zip(self,todir,filename):
        try:
            z = ZipFile("downloads/"+filename,"r")
        except:
            print "File corrupt"
            return
        
        if self.mode == "engine":
            root = "./"
            block = None
        #Extract folder from zip to todir
        elif filename+"/" in z.namelist():
            root = todir+"/"
            block = filename+"/"
        #Create folder from filename, extract contents of zip to there
        else:
            root = todir+"/"+filename+"/"
            try:
                os.makedirs(root)
            except:
                pass
            block = None
        for name in z.namelist():
            if hasattr(self,"progress"):
                self.progress.text = "extracting:"+name
            print "extract:",name
            txt = z.read(name)
            if block:
                if not name.startswith(block):
                    continue
            if "/" in name and not os.path.exists(root+name.rsplit("/",1)[0]):
                os.makedirs(root+name.rsplit("/",1)[0])
            if not name.endswith("/"):
                f = open(root+name,"wb")
                f.write(txt)
                f.close()
        z.close()
        os.remove("downloads/"+filename)
        try:
            os.remove("downloads/last")
        except:
            pass
    def download(self):
        t = threading.Thread(target=self.do_downloads)
        t.start()
    def upload(self):
        t = threading.Thread(target=self.do_uploads)
        t.start()
    def update(self):
        t = threading.Thread(target=self.do_update)
        t.start()
    def End_updater(self,*args):
        self.running = False
    def do_update(self,output=False):
        for x in list.children[2:]:
            if x.checked:
                print x
                if not hasattr(self,"progress"):
                    self.progress = progress()
                    root.add_child(self.progress)
                self.progress.height = 20
                self.progress.width = 400
                self.progress.rpos[1] = list.rpos[1]+list.height+20
                self.progress.progress = 0
                serv = urllib2.urlopen(self.dl_url+x.file)
                size = int(serv.info()["Content-Length"])
                read = 0
                bytes = 0
                cli = open("update.zip","wb")
                s = time.time()
                bps = 0
                while not Engine.quit_threads:
                    r = serv.read(1024)
                    if not r: break
                    cli.write(r)
                    read += len(r)
                    bytes += len(r)
                    self.progress.progress = read/float(size)
                    if time.time()-s>1:
                        bps = bytes/(time.time()-s)
                        s = time.time()
                        bytes = 0
                    self.progress.text = "%.02dKB/%.02dKB : %.02d KB/s"%(read/1000.0,size/1000.0,bps/1000.0)
                    if output:
                        self.progress.rpos = [0,0]
                        self.progress.draw(screen)
                        pygame.display.flip()
                        for evt in pygame.event.get():
                            if evt.type == pygame.QUIT: raise SystemExit
                serv.close()
                cli.close()
                root.children.remove(self.progress)
                list.children.remove(x)
                if os.path.exists("update.zip"):
                    z = ZipFile("update.zip","r")
                    for name in z.namelist():
                        txt = z.read(name)
                        print name
                        if "/" in name:
                            try:
                                os.makedirs("./"+name.rsplit("/",1)[0])
                            except:
                                pass
                        try:
                            f = open("./"+name,"wb")
                            f.write(txt)
                            f.close()
                        except:
                            pass
                    z.close()
                    os.remove("update.zip")
                list.status_box.text = "Update completed."
                del self.progress
                
def run():
    screen = pygame.display.set_mode([400,480])
    e = Engine()
    e.running = True
    start = button(e,"download")
    start.rpos[1] = list.rpos[1]+list.height
    end = button(e,"End updater")
    end.rpos[1] = start.rpos[1]+50
    root.add_child(start)
    root.add_child(end)
    root.start_index = root.children.index(start)

    char_b = button(e,"Download Characters")
    #char_b.rpos[0]=label.rpos[0]+label.width
    char_b.rpos[1]=20
    char_b.draw(screen)
    root.add_child(char_b)
    bg_b = button(e,"Download Backgrounds")
    bg_b.rpos[0]=char_b.rpos[0]+char_b.width+5
    bg_b.rpos[1]=20
    bg_b.draw(screen)
    root.add_child(bg_b)
    fg_b = button(e,"Download Foreground")
    fg_b.rpos[0]=bg_b.rpos[0]+bg_b.width+5
    fg_b.rpos[1]=20
    fg_b.draw(screen)
    root.add_child(fg_b)
    game_b = button(e,"Download Games")
    game_b.rpos[0]=0
    game_b.rpos[1]=40
    game_b.draw(screen)
    root.add_child(game_b)
    music_b = button(e,"Download Music")
    music_b.rpos[0]=game_b.rpos[0]+game_b.width+5
    music_b.rpos[1]=40
    music_b.draw(screen)
    root.add_child(music_b)
    info_label = editbox(None, "Hold shift to select multiple items in a category")
    root.add_child(info_label)
    info_label.draw_back = False
    info_label.rpos[0]=0
    info_label.rpos[1]=60
    
    pwup_b = button(e,"Update PyWright")
    pwup_b.rpos[1]=80
    pwup_b.rpos[0]=300
    pwup_b.draw(screen)
    root.add_child(pwup_b)
    
    if os.path.exists("downloads/last"):
        last_path,last_dl = open("downloads/last","r").read().split(" ")
        e.extract_zip(last_path,last_dl)

    clock = pygame.time.Clock()
    while e.running:
        mp = pygame.mouse.get_pos()
        clock.tick(60)
        screen.fill([225,225,225])
        root.draw(screen)
        pygame.display.flip()
        pygame.event.pump()
        quit = root.handle_events(pygame.event.get())
        if quit:
            Engine.quit_threads = True
            e.running = False
if __name__=="__main__":
    run()