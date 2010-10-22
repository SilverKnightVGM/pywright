
from errors import script_error



import pickle
import zlib
import os,sys
if sys.platform=="win32":
    os.environ['SDL_VIDEODRIVER']='windib'
import random
from core import *
import gui
import save
import load
from pwvlib import *

d = get_data_from_folder(".")
__version__ = d["version"]
VERSION = "Version "+cver_s(d["version"])

def pauseandquit():
    import time
    end = time.time()+5
    while time.time()<end:
        pass
    sys.exit()

#~ import psyco
#~ pscyo.full()
ALLTYPES = ["crossexam","files","objects",
"text","effect","evidence","debug",
"gameflow","animation","music","logic",
"interface","sounds"]
def category(cat,type=None):
    def _dec(f):
        f.cat = cat
        if type:
            assert type in ALLTYPES
            f.ftype = type
        f.name = [""]
        return f
    return _dec
class DOCTYPE():
    def __init__(self,name,description="",default=None):
        self.name = name
        self.description = description
        self.default = default
    def __repr__(self):
        s = self.__class__.__name__+" ( "+self.name+":"+self.description+" ) "
        if self.default is not None:
            s+="default:"+repr(self.default)
        return s
class COMBINED(DOCTYPE):
    """Set of arguments joined as text"""
class KEYWORD(DOCTYPE):
    """A value assigned by name"""
class TOKEN(DOCTYPE):
    """This exact token string may be present"""
class VALUE(DOCTYPE):
    """A named value, assigned by position"""
class ETC(DOCTYPE):
    """Each following argument is a separate entity, all potentially optional"""
class CHOICE():
    """One of these options should be present here"""
    def __init__(self,options):
        self.options = options
    def __repr__(self):
        return self.__class__.__name__+" ["+" ".join(repr(o) for o in self.options)+"]"

    
delete_on_menu = [evidence,portrait,fg]
only_one = [textbox,testimony_blink,evidence_menu]
def addob(ob):
    if [1 for x in only_one if isinstance(ob,x)]:
        for o2 in assets.cur_script.obs[:]:
            if isinstance(o2,ob.__class__):
                o2.kill = 1
    assets.cur_script.obs.append(ob)
def addevmenu():
    try:
        em = evidence_menu(assets.items)
        addob(em)
    except art_error,e:
        assets.cur_script.obs.append(error_msg(e.value,"",0,assets.cur_script))
        import traceback
        traceback.print_exc()
        return
    return em
def add_s(scene):
    s = Script()
    s.init(scene)
    assets.stack.append(s)
assets.addob = addob
assets.addevmenu = addevmenu
assets.addscene = add_s

def parseargs(arglist,intvals=[],defaults = {},setzero = {}):
    kwargs = {}
    for k in defaults:
        kwargs[str(k)] = defaults[k]
    args = []
    for a in arglist:
        if "=" in a:
            a = a.split("=",1)
            if a[0] in intvals: 
                try:
                    kwargs[str(a[0])] = int(a[1])
                except:
                    kwargs[str(a[0])] = float(a[1])
            else: 
                kwargs[str(a[0])]=a[1]
        elif setzero.has_key(a):
            kwargs[str(setzero[a])]=0
        else:
            kwargs[str(a)] = 1
    return kwargs,args
    
def argsort(list,arg="pri",get=getattr):
    def _cmp(a,b):
        return cmp(get(a,arg),get(b,arg))
    list.sort(_cmp)
def getz(ob,arg):
    v = getattr(ob,arg)
    if type(v)==type(""):
        v = assets.variables.get(v,0)
    return v

class World:
    """A collection of objects"""
    def __init__(self,obs=None):
        if not obs: obs = []
        self.all = obs[:]
        for o in self.all:
            o.cur_script = assets.cur_script
    def render_order(self):
        """Return a list of objects in the order they should
        be rendered"""
        class mylist(list): pass
        n = mylist(self.all[:])
        if assets.variables.get("_layering_method","zorder") == "zorder":
            argsort(n,"z")
        else:
            pass
        oldapp = n.append
        def _app(ob):
            self.append(ob)
            oldapp(ob)
        n.append = _app
        return n
    def click_order(self):
        """Return a list of objects in the order they should
        be checked for clicks"""
        n = reversed(self.render_order())
        return n
    def update_order(self):
        """Return a list of objects in the order they
        should be updated"""
        n = self.all[:]
        argsort(n,"pri")
        return n
    def select(self):
        """Return a list of objects that match the query"""
    def append(self,ob):
        self.all.append(ob)
        ob.cur_script = assets.cur_script
    def extend(self,obs,unique=True):
        if unique:
            for o in obs:
                if o not in self.all:
                    self.all.append(o)
        else:
            self.all.extend(o)
    def remove(self,ob):
        self.all.remove(ob)
assets.World = World


def EVAL(stuff):
    stuff = stuff.split(" ",2)
    if len(stuff)==1:
        return assets.variables.get(stuff[0],"")
    if len(stuff)==2:
        stuff = stuff[0],"=",stuff[1]
    current,op,check = stuff
    if op not in ["<",">","=","<=",">="]:
        check = op+" "+check
        op = "="
    current = assets.variables.get(current)
    if op=="=":op="=="
    if op!="==":
        current = int(current)
        check = int(check)
    if op == ">":
        return current > check
    elif op == "<":
        return current < check
    elif op == "==":
        return current == check
    elif op == "<=":
        return current <= check
    elif op == ">=":
        return current >= check
def GV(v):
    if v[0].isdigit():
        if "." in v:
            return float(v)
        return int(v)
    if v.startswith("'") and v.endswith("'"):
        return v[1:-1]
    v = assets.variables.get(v,"")
    if v[0].isdigit():
        if "." in v:
            return float(v)
        return int(v)
    return v
def ADD(statements):
    return GV(statements[0])+GV(statements[1])
def MUL(statements):
    return GV(statements[0])*GV(statements[1])
def MINUS(statements):
    return GV(statements[0])-GV(statements[1])
def DIV(statements):
    return GV(statements[0])/GV(statements[1])
def EQ(statements):
    return str(GV(statements[0])==GV(statements[1])).lower()
def GTEQ(statements):
    return str(GV(statements[0])>=GV(statements[1])).lower()
def GT(statements):
    return str(GV(statements[0])>GV(statements[1])).lower()
def LT(statements):
    return str(GV(statements[0])<GV(statements[1])).lower()
def LTEQ(statements):
    return str(GV(statements[0])<=GV(statements[1])).lower()
def AND(statements):
    if vtrue(statements[0]) and vtrue(statements[1]):
        return "true"
    return "false"
def OR(stuff):
    for line in stuff:
        if EVAL(line):
            return True
    return False
def OR2(statements):
    if vtrue(statements[0]) or vtrue(statements[1]):
        return "true"
    return "false"
def EXPR(line):
    statements = []
    cur = ""
    paren = []
    quote = []
    for word in line.split(" "):
        if not paren and not quote and word == "+":
            statements.append(ADD)
        elif not paren and not quote and word == "*":
            statements.append(MUL)
        elif not paren and not quote and word == "-":
            statements.append(MINUS)
        elif not paren and not quote and word == "/":
            statements.append(DIV)
        elif not paren and not quote and word == "==":
            statements.append(EQ)
        elif not paren and not quote and word == "<=":
            statements.append(LTEQ)
        elif not paren and not quote and word == ">=":
            statements.append(GTEQ)
        elif not paren and not quote and word == "<":
            statements.append(LT)
        elif not paren and not quote and word == ">":
            statements.append(GT)
        elif not paren and not quote and word == "AND":
            statements.append(AND)
        elif not paren and not quote and word == "OR":
            statements.append(OR2)
        elif word.strip():
            if paren:
                if word.endswith(")"):
                    paren.append(word)
                    statements.append(EXPR(" ".join(paren)[1:-1]))
                    paren = []
                else:
                    paren.append(word)
            elif quote:
                quote.append(word)
                if word.endswith("'"):
                    statements.append(" ".join(quote))
                    quote = []
            elif word.startswith("(") and word.endswith(")"):
                statements.append(word[1:-1])
            elif word.startswith("("):
                paren.append(word)
            elif word.startswith("'") and word.endswith("'"):
                statements.append(word)
            elif word.startswith("'"):
                quote.append(word)
            else:
                statements.append(word)
    return statements
def EVAL_EXPR(expr):
    if not isinstance(expr,list):
        return str(expr)
    if len(expr)==1:
        return EVAL_EXPR(expr[0])
    oop = [MUL,DIV,ADD,MINUS,EQ,LT,GT,LTEQ,GTEQ,OR2,AND]
    ops = []
    for i,v in enumerate(expr):
        if v in oop:
            ops.append((i,v))
    if not ops:
        return str(expr[0])
    ops.sort(key=lambda x: oop.index(x[1]))
    op = ops[0]
    left = expr[op[0]-1:op[0]]
    right = expr[op[0]+1:op[0]+2]
    left = EVAL_EXPR(left)
    right = EVAL_EXPR(right)
    v = op[1]([left,right])
    expr[op[0]-1] = v
    del expr[op[0]]
    del expr[op[0]]
    return EVAL_EXPR(expr)

assert EVAL_EXPR(EXPR("5 + 1 + 3 * 10"))=="36"
assert EVAL_EXPR(EXPR("2 * (5 + 1)"))=="12"
assert EVAL_EXPR(EXPR("'funny ' + 'business'"))=="funny business"
assert vtrue(EVAL_EXPR(EXPR("2 * (5 + 1) == (5 + 1) * 2")))
assets.variables["something"] = "1"
assert EVAL_EXPR(EXPR("5 + something + 3 * 10"))=="36"
del assets.variables["something"]
assert EVAL_EXPR(EXPR("(5 == 4 OR 5 == 5) AND (1 + 3 == 4) AND ('funny' = 'not funny')"))=="false"
assert EVAL_EXPR(EXPR("(5 == 4 OR 5 == 5) AND (1 + 3 == 4) OR ('funny' = 'not funny')"))=="true"
assert EVAL_EXPR(EXPR("5 > 3"))=="true"
assert EVAL_EXPR(EXPR("5 > 6"))=="false"
assert EVAL_EXPR(EXPR("5 < 3"))=="false"
assert EVAL_EXPR(EXPR("5 < 6"))=="true"
assert EVAL_EXPR(EXPR("5 >= 3"))=="true"
assert EVAL_EXPR(EXPR("5 >= 5"))=="true"
assert EVAL_EXPR(EXPR("5 >= 6"))=="false"
assert EVAL_EXPR(EXPR("5 <= 3"))=="false"
assert EVAL_EXPR(EXPR("5 <= 5"))=="true"
assert EVAL_EXPR(EXPR("5 <= 6"))=="true"

class Script(gui.widget):
    save_me = True
    def __init__(self,parent=None):
        self.world = World()
        
        #widget stuff
        self.rpos = [0,0]
        self.parent = parent
        self.viewed = {}  #keeps track of viewed textboxes
        self.imgcache = {}  #Used to preload images
        self.lastline = ""  #Remember where we jumped from in a script so we can go back
        self.lastline_value = ""   #Remember last line we executed
        self.held = []
    obs = property(lambda self: self.world.render_order(),lambda self,val: setattr(self,"world",World(val)))
    upobs = property(lambda self: self.world.update_order())
    def _gchildren(self): return self.world.click_order()
    children = property(_gchildren)
    width = property(lambda x: sw)
    height = property(lambda x: sh*2)
    def handle_events(self,evts):
        n = []
        dp = translate_click
        for e in evts:
            if e.type==pygame.MOUSEMOTION:
                d = {"rel":e.rel,"buttons":e.buttons}
                d["pos"] = dp(e.pos)
                e = pygame.event.Event(pygame.MOUSEMOTION,d)
            if e.type==pygame.MOUSEBUTTONUP:
                d = {"button":e.button}
                d["pos"] = dp(e.pos)
                e = pygame.event.Event(pygame.MOUSEBUTTONUP,d)
            if e.type==pygame.MOUSEBUTTONDOWN:
                d = {"button":e.button}
                d["pos"] = dp(e.pos)
                e = pygame.event.Event(pygame.MOUSEBUTTONDOWN,d)
            n.append(e)
        gui.widget.mouse_pos = dp(pygame.mouse.get_pos())
        gui.widget.handle_events(self,n)
    def save(self):
        props = {}
        save.cp(["scene","si","cross","statement","instatement","lastline","pri","viewed"],self,props)
        if self.parent:
            props["_parent_index"] = assets.stack.index(self.parent)
        obs = []
        for ob in self.world.all:
            save_state = save.save(ob)
            if save_state:
                obs.append(save_state)
        props["_objects"] = obs
        props["_world_id"] = id(self.world)
        return ["assets.Script",[],props,["stack",assets.stack.index(self)]]
    def after_load(self):
        p = {}
        for k in ["si","cross","statement","instatement","lastline","pri","viewed"]:
            p[k] = getattr(self,k,"")
        self.init(self.scene)
        for k in p:
            setattr(self,k,p[k])
        if hasattr(self,"_parent_index"):
            try:
                self.parent = assets.stack[self._parent_index]
            except IndexError:
                pass
        obs = []
        after_after = []
        if not hasattr(self,"_world_id"):
            self._world_id = id(self)
        if self._world_id in assets.loading_cache:
            self.world = assets.loading_cache[self._world_id]
            return
        assets.loading_cache[self._world_id] = self.world
        for o in getattr(self,"_objects",[]):
            try:
                o,later = load.load(self,o)
            except:
                continue
            if o:
                obs.append(o)
            if later:
                after_after.append(later)
        self.world.all = obs
        for of in after_after:
            of()
    def load(self,s):
        vals = pickle.loads(s)
        self.scene,self.si,self.cross,self.statement,self.instatement,self.lastline,self.pri = vals[:7]
        self.init(self.scene)
        self.scene,self.si,self.cross,self.statement,self.instatement,self.lastline,self.pri = vals[:7]
        if len(vals)>7:
            self.viewed = vals[7]
        self.si-=1
    def init(self,scene="",macros=True,ext=".txt",scriptlines=None):
        self.imgcache.clear()
        self.scene = scene
        self.scriptlines = []
        self.macros = {}
        if scriptlines:
            self.scriptlines = scriptlines
            self.macros = assets.parse_macros(self.scriptlines)
        self.si = 0
        self.cross = None
        self.statement = ""
        self.instatement = False
        self.lastline = 0
        self.pri = 0
        
        self.held = []
        #~ if vtrue(assets.variables.get("_preload","on")):
            #~ self.preload()
        if scene:
            try:
                self.scriptlines = assets.open_script(scene,macros,ext)
            except Exception,e:
                import traceback
                traceback.print_exc()
                #@self.obs.append(error_msg(e.value,self.lastline_value,self.si,self))
                self.scriptlines = ['"error opening script{n}\'%s\'"'%scene]
                return True
            self.macros = assets.macros
        self.labels = []
        for i,line in enumerate(self.scriptlines):
            if line.startswith("label ") or line.startswith("result "):
                rn = line.split(" ",1)[1].strip().replace(" ","_")
                if rn:
                    self.labels.append([rn,i])
            if line.startswith("list ") or line.startswith("cross ") or line.startswith("statement "):
                rn = line.split(" ",1)[1].strip().replace(" ","_")
                if rn:
                    self.labels.append([rn,i-1])

        return True
    def preload(self):
        old = self.obs[:]
        self.obs = []
        import time
        t = time.time()
        nt = time.time()
        for line in self.scriptlines:
            if line.strip().startswith("set _preload") and line[13:].strip() in ["0","off","false"]:
                return
            if line.strip()=="preload_cancel": return
            try:
                args = [x for x in line.split(" ")]
            except:
                pass
            if not args: continue
            if args[0] not in ["bg","char","fg","ev"]: continue
            func = getattr(self,"_"+args[0],None)
            if func:
                try:
                    func(*args)
                except:
                    pass
            nt = time.time()
            if nt-t>1.5:
                pygame.screen.blit(arial14.render("Loading Script...",1,[255,255,255]),[0,100])
                draw_screen()
        self.obs = old[:]
    def getline(self):
        try:
            line = self.scriptlines[self.si]
            line = line.replace("\t","    ")
            line = line.replace("\r","").replace("\n","")
            line = line.rsplit("#",1)[0]
            line = line.rsplit("//",1)[0]
            self.lastline_value = line.strip()
            return line.strip()
        except TypeError:
            return
        except IndexError:
            return
    def update_objects(self):
        for o in self.world.update_order():
            if o.update():
                if o.cur_script==self: return False
        return True
    def update(self):
        try:
            if self.update_objects():
                self.interpret()
        except script_error,e:
            self.obs.append(error_msg(e.value,self.lastline_value,self.si,self))
            import traceback
            traceback.print_exc()
            return
        except art_error,e:
            if vtrue(assets.variables.get("_debug","false")):
                self.obs.append(error_msg(e.value,self.lastline_value,self.si,self))
                import traceback
                traceback.print_exc()
                return
        except markup_error,e:
            self.obs.append(error_msg(e.value,self.lastline_value,self.si,self))
            import traceback
            traceback.print_exc()
            return
        except Exception,e:
            self.obs.append(error_msg("Undefined:"+e.message,self.lastline_value,self.si,self))
            import traceback
            traceback.print_exc()
            return
    def draw(self,screen):
        for o in self.obs:
            if not getattr(o,"hidden",False) and not getattr(o,"kill",False):
                o.draw(screen)
        if vtrue(assets.variables.get("_debug","false")):
            screen.blit(assets.get_font("nt").render("debug",1,[240,240,240]),[220,0])
    def tboff(self):
        for o in self.obs:
            if isinstance(o,testimony_blink):
                self.world.remove(o)
                break
    def tbon(self):
        addob(testimony_blink("testimony"))
    def state_test_true(self,test):
        if test is None:
            return True
        return vtrue(assets.variables.get(test,"false"))
    def refresh_arrows(self,tbox):
        arrows = [x for x in self.obs if isinstance(x,uglyarrow) and not getattr(x,"kill",0)]
        for a in arrows:
            a.kill = 1
        if vtrue(assets.variables.get("_textbox_show_button","true")):
            u = uglyarrow()
            self.obs.append(u)
            u.textbox = tbox
            if assets.variables.get("_statements",[]):
                statements = [x for x in assets.variables["_statements"] if self.state_test_true(x["test"])]
                if statements and (statements[0]["words"] == self.statement) or not self.statement:
                    u.showleft = False
                else:
                    u.showleft = True
                    tbox.showleft = True
    def interpret(self):
        self.buildmode = True
        exit = False
        while self.buildmode and not exit:
            line = self.getline()
            while not line:
                if line is None: 
                    return self._endscript()
                self.si += 1
                line = self.getline()
            #print "exec(",repr(line),")"
            self.si += 1
            assets.variables["_currentline"] = str(self.si)
            exit = self.execute_line(line)
    @category([COMBINED("text","Text to be print in the textbox, with markup.","")],type="text")
    def _textbox(self,line):
        """Draws a several line animated textbox to the screen. Uses art/general/textbox_2 as the back
        drop. The letters of the textbox will print one by one at a set rate, which can be modified
        with the markup commands. If there is a character speaking (the _speaking variable is set, a char
        command has just been issued, etc) then the character will animate as the text is output.
        The game script will pause until the player (or the textbox via markup) tells the game to 
        continue. This command can also be issued by having a blank line surrounded by quotes. Ex:
{{{
char test
textbox This is some text that is printing
#The same text could be printed this way:
char test
"This is some text that is printing."
}}}"""
        text = line.replace("{n}","\n")
        tbox = textbox(text)
        tbox.showleft=False
        if not self.viewed.get(assets.game+self.scene+str(self.si-1)):
            tbox.can_skip = False
        if vtrue(assets.variables.get("_debug","false")):
            tbox.can_skip = True
        if vtrue(assets.variables.get("_textbox_allow_skip","false")):
            tbox.can_skip = True
        self.viewed[assets.game+self.scene+str(self.si-1)] = True
        addob(tbox)
        self.refresh_arrows(tbox)
        self.tboff()
        if self.cross is not None and self.instatement:
            self.tbon()
            if self.cross == "proceed":
                tbox.statement = self.statement
                nt,t = tbox._text.split("\n",1)
                tbox._text = nt+"\n{c283}"+t
                #tbox.color = (20,200,40)
    def execute_line(self,line):
        if line[0] in [u'"',u'\u201C'] and len(line)>1:
            self.call_func("textbox",[line[1:-1]])
            return True
        def repvar(x):
            if x.startswith("$") and not x[1].isdigit():
                return assets.variables[x[1:]]
            elif x.startswith("$"):
                return u""
            if u"=" in x:
                spl = x.split(u"=",1)
                if spl[1].startswith(u"$"):
                    return spl[0]+u"="+assets.variables[spl[1][1:]]
            return x
        args = []
        try:
            args = [repvar(x) for x in line.split(u" ")]
        except KeyError:
            self.obs.append(error_msg("Variable not defined:",line,self.si,self))
            return True
        if self.execute_macro(args[0]):
            return True
        self.call_func(args[0],args)
    def call_func(self,command,args):
        func = getattr(self,"_"+command,None)
        if func:
            func(*args)
        elif vtrue(assets.variables.get("_debug","false")): 
            self.obs.append(error_msg("Invalid command:"+command,line,self.si,self))
            return True
    def execute_macro(self,macroname,args="",obs=None):
        mlines = self.macros.get(macroname,None)
        if not mlines: return
        if args: args = " "+args
        nscript = Script(self)
        nscript.world = self.world
        scriptlines = ["{"+macroname+args+"}"]
        assets.replace_macros(scriptlines,self.macros)
        nscript.init(scriptlines=scriptlines)
        nscript.macros = self.macros
        assets.stack.append(nscript)
        self.buildmode = False
        return nscript
    def next_statement(self):
        if not assets.variables.get("_statements",[]):
            return
        which = None
        for s in assets.variables["_statements"]:
            if not self.state_test_true(s["test"]):
                continue
            #return
            if s["index"]>self.si and s["words"]!=self.statement:
                which = s["index"]
                break
        if which is not None:
            self.si = which
    def prev_statement(self):
        if not assets.variables.get("_statements",[]):
            return
        which = None
        for s in reversed(assets.variables["_statements"]):
            if not self.state_test_true(s["test"]):
                continue
            if s["index"]<self.si and s["words"]!=self.statement:
                which = s["index"]
                break
        if which is not None:
            self.si = which
        else:
            self.si -= 1
    def goto_result(self,name,wrap=False,backup="none"):
        for o in self.obs:
            if isinstance(o,guiWait): o.kill = 1
        if name.startswith("{") and name.endswith("}"):
            self.execute_macro(name[1:-1])
            return
        name = name.replace(" ","_")
        wrap=True
        first = None
        self.lastline = self.si
        self.instatement = False
        assets.variables["_lastline"] = str(self.si)
        for label,index in self.labels:
            if not first and label==name:
                first = index
                assets.variables["_currentlabel"] = label
            if label == name and index>=self.si:
                self.si = index+1
                assets.variables["_currentlabel"] = label
                return
            if label == backup and index>self.si:
                self.si = index+1
                assets.variables["_currentlabel"] = backup
                return
        if first is not None and wrap:
            self.si = first+1
            return
        try:
            name = int(name)-1
        except:
            raise script_error,"no label \"%s\" to go to in %s"%(name,self.labels)
        if name>=len(self.scriptlines) or name<0:
            raise script_error,"Trying to go to invalid line number"
        self.si = name+1
    @category([COMBINED("text","Some text to print")],type="debug")
    def _print(self,*args):
        """Prints some text to the logfile. Only useful for debugging purposes."""
        print " ".join(args[1:])
    @category([],type="gameflow")
    def _endscript(self,*args):
        """Ends the currently running script and pops it off the stack. Multiple scripts
        may be running in PyWright, in which case the next script on the stack will
        resume running."""
        self.buildmode = False
        if self in assets.stack:
            assets.stack.remove(self)
            if "enter" in self.held: self.held.remove("enter")
            if self.parent:
                self.parent.held = []
                self.parent.world = self.world
        if not assets.stack:
            assets.variables.clear()
            assets.stop_music()
            assets.stack[:] = []
            make_start_script(False)
        return
    @category([CHOICE([TOKEN("true","turns on debug mode"),TOKEN("false","turns off debug mode")])],type="debug")
    def _debug(self,command,value):
        """Used to turn debug mode on or off. Debug mode will print more errors to the screen,
        and allow you to skip through any text."""
        if value.lower() in ["on","1","true"]:
            assets.variables["_debug"] = "on"
        else:
            assets.variables["_debug"] = "off"
    @category([COMBINED("label text","The name of this section of code")],type="logic")
    def _label(self,command,*name):
        """Used to mark a spot in a wrightscript file. Other code can then refer to this spot,
        specifically for making the code reader "goto" this spot."""
        assets.variables["_lastlabel"] = " ".join(name)
    @category([VALUE("game","Path to game. Should be from the root, i.e. games/mygame or games/mygame/mycase"),
                    VALUE("script","Script to look for in the game folder to run first","intro")],type="gameflow")
    def _game(self,command,game,script="intro"):
        """Can be used to start a new game or case."""
        for o in self.obs[:]:
            o.kill = 1
        assets.clear()
        assets.game = game
        self.held = []
        scene = script
        #assets.addscene(scene)
        self.init(scene)
    @category([COMBINED("destination","The destination label to move to"),
                    KEYWORD("fail","A label to jump to if the destination can't be found")],type="logic")
    def _goto(self,command,place,*args):
        """Makes the script go to a different section, based on the label name."""
        fail = None
        for x in args:
            if "=" in x:
                k,v = x.split("=",1)
                if k == "fail":
                    fail = v
        self.goto_result(place,wrap=True,backup=fail)
    @category([COMBINED("flag_expression","list of flag names joined with AND or OR"),
                    CHOICE([
                    TOKEN("?"),VALUE("label","label to jump to if the evaluation is true")
                    ]),
                    KEYWORD("fail","label to jump to if evaluation is false","none")],type="logic")
    def flag_logic(self,value,*args):
        fail=None
        args = list(args)
        label = args.pop(-1)
        if label.startswith("fail="):
            fail=label.split("=",1)[1]
            label = args.pop(-1)
        if label.endswith("?"):
            args.append(label[:-1])
            label = "?"
        sentance = ""
        mode = 0
        for a in args:
            if mode == 0:
                sentance+="('"+a+"' in assets.variables)"
            elif mode == 1:
                if a=="AND": sentance+=" and "
                elif a=="OR": sentance+=" or "
                else: raise script_error("Logic must be AND or OR")
            mode = 1-mode
        if not eval(sentance)==value: return self.fail(label,fail)
        self.succeed(label)
    @category(flag_logic.cat)
    def _noflag(self,command,*args):
        """Evaluates an expression with flag names. If the expression
        is not true, jumps to the listed label. Otherwise, will
        jump to the fail keyword if that was given. If the line ends
        with a '?', it will execute the next line and the next line only
        when the flag expression is false."""
        self.flag_logic(False,*args)
    @category(flag_logic.cat)
    def _flag(self,command,*args):
        """Evaluates an expression with flag names. If the expression
        is true, jumps to the listed label. Otherwise, will
        jump to the fail keyword if that was given. If the line ends
        with a '?', it will execute the next line and the next line only
        when the flag expression is true."""
        self.flag_logic(True,*args)
    @category([VALUE('flag_name','flag to set')],type="logic")
    def _setflag(self,command,flag):
        """Sets a flag. Shorthand for setting a variable equal to true. Flags
        will remain set for the remainder of the game, and can be used to
        track what a player has done."""
        if flag not in assets.variables: assets.variables[flag]="true"
    @category([VALUE('flag_name','flag to unset')],type="logic")
    def _delflag(self,command,flag):
        """Deletes a flag. Flags will remain set for the remainder of the game, but
        can be forgotten with delflag."""
        if flag in assets.variables: del assets.variables[flag]
    @category([VALUE("variable","variable name to set"),COMBINED("value","Text to assign to the variable. Can include $x to replace words of the text with the value of other variables.")],type="logic")
    def _set(self,command,variable,*args):
        """Sets a variable to some value."""
        value = u" ".join(args)
        assets.variables[variable]=value
    @category([VALUE("variable","variable name to set"),COMBINED("expression2","The results of the expression will be stored in the variable.")],type="logic")
    def _set_ex(self,command,variable,*args):
        """Sets a variable to some value based on an expression"""
        value = EVAL_EXPR(EXPR(" ".join(args)))
        assets.variables[variable]=value
    @category([VALUE("destination variable","The variable to save the value into"),COMBINED("source variable","The variable to get the value from. Can use $x to use another variable to point to which variable to copy from, like a signpost.")],type="logic")
    def _getvar(self,command,variable,*args):
        """Copies the value of one variable into another."""
        value = u"".join(args)
        assets.variables[variable]=assets.variables.get(value,"")
    _setvar = _set
    _setvar_ex = _set_ex
    @category([VALUE("variable","variable name to save random value to"),VALUE("start","smallest number to generate"),VALUE("end","largest number to generate")],type="logic")
    def _random(self,command,variable,start,end):
        """Generates a random integer with a minimum
        value of START, a maximum value of END, and
        stores that value to VARIABLE"""
        random.seed(pygame.time.get_ticks()+random.random())
        value = random.randint(int(start),int(end))
        assets.variables[variable]=str(value)
    @category([VALUE("variable","variable to save value to"),COMBINED("words","words to join together")],type="logic")
    def _joinvar(self,command,variable,*args):
        """Takes a series of words and joins them together, save the joined
string to a variable. For instance:
{{{setvar hour 3
setvar minute 15
joinvar time $hour : $minute
"{$time}"}}}
will output "3:15"
"""
        value = "".join(args)
        assets.variables[variable]=value
    @category([VALUE("variable","variable to save to"),VALUE("amount","amount to add to the variable")],type="logic")
    def _addvar(self,command,variable,value):
        """Adds an amount to a variable. If the variable 'x' were set to 4, the script:
{{{addvar x 1}}}
would set 'x' to 5."""
        oldvalue = int(assets.variables.get(variable,0))
        oldvalue += int(value)
        assets.variables[variable] = str(oldvalue)
    @category([VALUE("variable","variable to subtract from and save to"),VALUE("amount","amount to subtract from the variable")],type="logic")
    def _subvar(self,command,variable,value):
        """Subtract an amount from a variable. If the variable 'x' were set to 33, the script:
{{{subvar x 3}}}
would set 'x' to 30."""
        oldvalue = int(assets.variables[variable])
        oldvalue -= int(value)
        assets.variables[variable] = str(oldvalue)
    @category([VALUE("variable","variable to save to"),VALUE("amount","amount to multiply the variable by")],type="logic")
    def _mulvar(self,command,variable,value):
        """Multiply a variable by a number. If the variable 'x' were set to 5, the script:
{{{mulvar x 3}}}
would set 'x' to 15."""
        oldvalue = int(assets.variables[variable])
        oldvalue *= int(value)
        assets.variables[variable] = str(int(oldvalue))
    @category([VALUE("variable","variable to save to"),VALUE("amount","amount to divide the variable by")],type="logic")
    def _divvar(self,command,variable,value):
        """Divide a variable by a number. If the variable 'x' were set to 10, the script:
{{{divvar x 2}}}
would set 'x' to 5."""
        oldvalue = int(assets.variables[variable])
        oldvalue /= float(value)
        assets.variables[variable] = str(int(oldvalue))
    @category([VALUE("variable","variable to save to")])
    def _absvar(self,command,variable):
        """Force a variable to be positive. If the variable 'x' were set to -12, the script:
{{{absvar x}}}
would set 'x' to 12."""
        oldvalue = int(assets.variables.get(variable,0))
        oldvalue = abs(int(oldvalue))
        assets.variables[variable] = str(oldvalue)
    @category([VALUE("filename","file to export variables into, relative to the case folder"),
            ETC("variable_names",
                "The names of variables to export. If none are listed, all variables will be exported",
                "all variables")],type="files")
    def _exportvars(self,command,filename,*vars):
        """Saves the name and value of listed variables to a file. They can later be restored. Can be used to make
        ad-hoc saving systems, be a way to store achievements separate from saved games, or other uses."""
        d = {}
        if not vars:
            vars = assets.variables.keys()
        for k in vars:
            d[k] = assets.variables.get(k,"")
        filename = filename.replace("..","").replace(":","")
        while filename.startswith("/"):
            filename = filename[1:]
        f = open(assets.game+"/"+filename,"w")
        f.write(repr(d))
        f.close()
    @category([VALUE("filename","file to import variables from, relative to the case folder")],type="files")
    def _importvars(self,command,filename):
        """Restores previously exported variables from the file."""
        filename = filename.replace("..","").replace(":","")
        while filename.startswith("/"):
            filename = filename[1:]
        try:
            f = open(assets.game+"/"+filename)
        except:
            return
        txt = f.read()
        f.close()
        if txt.strip():
            d = eval(txt)
            assets.variables.update(d)
    def autosave(self):
        if assets.autosave and vtrue(assets.variables.get("_allow_autosave","true")):
            assets.save_game("autosave")
    @category([VALUE("filename","File to save to, relative to case folder. Saved games may not be named 'hide'","save"),
            TOKEN("hide","If hide token is included, the interface wont inform the user of the save.")],type="files")
    def _savegame(self,command,*args):
        """Creates a new saved game in the case folder."""
        filename = "save"
        hide = False
        args = list(args)
        if "hide" in args:
            hide = True
            args.remove("hide")
        if args:
            filename = args[0]
        self.si += 1
        old = assets.variables.get("_allow_saveload","true")
        assets.variables["_allow_saveload"] = "true"
        assets.save_game(filename,hide)
        assets.variables["_allow_saveload"] = old
        self.si -= 1
    @category([VALUE("filename","Saved game to load, relative to case folder. Saved games may not be named 'hide'","save"),
            TOKEN("hide","If hide token is included, the interface wont inform the user of the load.")],type="files")
    def _loadgame(self,command,*args):
        """Restores a save file."""
        filename = "save"
        hide = False
        args = list(args)
        if "hide" in args:
            hide = True
            args.remove("hide")
        if args:
            filename = args[0]
        old = assets.variables.get("_allow_saveload","true")
        assets.variables["_allow_saveload"] = "true"
        assets.load_game(None,filename,hide)
        assets.variables["_allow_saveload"] = old
        return self._endscript()
    @category([VALUE("path","path, relative to game's directory, to save the screenshot, including file extension (.png or .jpg)"),
                    KEYWORD("width","shrink screenshot to this width",256),
                    KEYWORD("height","shrink screenshot to this height",192),
                    KEYWORD("x","x-value of region to screenshot",0),
                    KEYWORD("y","y-value of region to screenshot",0),
                    KEYWORD("rwidth","width of region to screenshot",256),
                    KEYWORD("rheight","height of region to screenshot",192)],type="files")
    def _screenshot(self,command,path,*args):
        """Takes a screenshot and saves the image. Can select a specific region of the screen to
        snapshot. Useful for custom interfaces, or just providing a snapshot feature."""
        root = assets.game.replace("\\","/").rsplit("/",1)[0]
        if root == "games" or root == "games":
            root = assets.game
        image = pygame.screen.convert()
        self.draw(image)
        resize = list(image.get_size())
        subrect = image.get_rect()
        for a in args:
            if a.startswith("width="):
                resize[0] = int(a.split("=")[1])
            if a.startswith("height="):
                resize[1] = int(a.split("=")[1])
            if a.startswith("x="):
                subrect.x = int(a.split("=")[1])
            if a.startswith("y="):
                subrect.y = int(a.split("=")[1])
            if a.startswith("rwidth="):
                subrect.width = int(a.split("=")[1])
            if a.startswith("rheight="):
                subrect.height = int(a.split("=")[1])
        image = image.subsurface(subrect)
        if resize:
            image = pygame.transform.scale(image,resize)
        pygame.image.save(image,root+"/"+path+".png")
        image = pygame.transform.scale(image,[50,50])
        pygame.real_screen.blit(image,[0,0])
        pygame.display.flip()
    @category(
                    [COMBINED('expression2'),
                    CHOICE([VALUE('label'),TOKEN('?')]),
                    KEYWORD('fail','label to jump to if expression fails')],type="logic")
    def _is_ex(self,command,*args):
        """Evaluates the expression. If the expression is true, will either jump to 'label' or execute the next
        line if a '?' is used instead of a label name. If 'fail=' is given, will jump to that label when the expression
        is false.
        
        Expressions are modelled after ace attorney online, and support () - + / * == < > <= >= AND and OR for
        operations, and var1 (variables), 'blah' (text) or 239 (numbers) for values. Functions are not 
        supported, use pywright operations to manipulate variables before using the 
        variable in an expression."""
        fail = None
        args = list(args)
        label = args.pop(-1)
        if label.startswith("fail="):
            fail = label.split("=",1)[1]
            label = args.pop(-1)
        if label.endswith("?"):
            args.append(label[:-1])
            label = "?"
        answer = EVAL_EXPR(EXPR(" ".join(args)))
        if vtrue(answer):
            return self.succeed(label)
        return self.fail(label,fail)
    @category([COMBINED('expression'),
                    KEYWORD('fail','label to jump to if expression fails'),
                    CHOICE([VALUE('label'),TOKEN('?')])],type="logic")
    def _is(self,command,*args):
        """Evaluates the expression. If the expression is true, will either jump to 'label' or execute the next
        line if a '?' is used instead of a label name. If 'fail=' is given, will jump to that label when the expression
        is false.
        
        Expressions are very simplistic, supporting only AND and OR for operations, and numbers/text
        or $variables for operands."""
        fail = None
        args = list(args)
        label = args.pop(-1)
        if label.startswith("fail="):
            fail = label.split("=",1)[1]
            label = args.pop(-1)
        if label.endswith("?"):
            args.append(label[:-1])
            label = "?"
        args = " ".join(args).split(" AND ")
        args = [x.split(" OR ") for x in args]
        args = [OR(x) for x in args]
        if False in args: return self.fail(label,fail)
        self.succeed(label)
    @category([COMBINED('expression','An expression that evaluates to true or false'),
                    KEYWORD('fail','label to jump to if expression fails'),
                    CHOICE([VALUE('label','a label to jump to if the expression evaluates to false'),TOKEN('?','execute next line only if expression evaluates to false')])],type="logic")
    def _isnot(self,command,*args):
        """If the expression is false, will jump to the success label.
        Otherwise, it will either continue to the next line, or jump to
        the label set by the fail keyword
        
        Expressions are very simplistic, supporting only AND and OR for operations, and numbers/text
        or $variables for operands."""
        fail = None
        args = list(args)
        label = args.pop(-1)
        if label.startswith("fail="):
            fail = label.split("=",1)[1]
            label = args.pop(-1)
        if label.endswith("?"):
            args.append(label[:-1])
            label = "?"
        args = " ".join(args).split(" AND ")
        args = [x.split(" OR ") for x in args]
        args = [OR(x) for x in args]
        if False in args: return self.succeed(label)
        self.fail(label,fail)
    @category([VALUE('variable',"Variable to check if it doesn't exist"),
                    CHOICE([VALUE('label','a label to jump to if the variable has not been set or is blank'),TOKEN('?','execute next line only if variable is unset or blank')])],type="logic")
    def _isempty(self,command,variable,label=None):
        """If the variable has not been set (it is equal to "") then either jump to the given label or 
        execute the next line if the given label is a '?'."""
        if variable.endswith("?"):
            variable = variable[:-1]
            label = "?"
        if not assets.variables.get(variable,None): return self.succeed(label)
        self.fail(label)
    @category([VALUE('variable','Variable to check if it exists'),
                    CHOICE([VALUE('label','a label to jump to if the variable has been set and is not blank'),TOKEN('?','execute next line only if variable is set and not blank')])],type="logic")
    def _isnotempty(self,command,variable,label=None):
        """If the variable has been set (it is not equal to "") then either jump to the given label or 
        execute the next line if the given label is a '?'."""
        if variable.endswith("?"):
            variable = variable[:-1]
            label = "?"
        if assets.variables.get(variable,None): return self.succeed(label)
        self.fail(label)
    def succeed(self,label=None,dest=None):
        """What happens when a test succeeds?"""
        if label == "?": label = None
        if label:
            self._goto(None,label)
        else:
            pass
    def fail(self,label=None,dest=None):
        if label == "?": label = None
        if dest:
            return self.goto_result(dest)
        if label:
            pass
        else:
            self.si += 1
    @category([VALUE('variable','Variable to check if it exists'),
                    CHOICE([VALUE('label','a label to jump to if the variable has been set and is not blank'),TOKEN('?','execute next line only if variable is set and not blank')])],type="logic")
    def _isnumber(self,command,*args):
        """If the variable contains a number jump to the given label or execute the next line if the given
        label is a '?'"""
        args = list(args)
        label = args.pop(-1)
        if label.endswith("?"):
            args.append(label[:-1])
            label = "?"
        value = " ".join(args)
        if value.isdigit():
            return self.succeed(label)
        return self.fail(label)
    @category([VALUE('ticks','How many ticks (1/60 of a second) to wait'),
TOKEN('all','Pause EVERYTHING','default behavior pauses script execution but lets animation continue'),
TOKEN('script','Pause only the script','this is the default behavior'),
KEYWORD('priority','Fine tune what gets paused and what doesnt.','10000 (such a high number for priority means that most objects will not be paused')
],type="animation")
    def _pause(self,command,*args):
        """This command will pause execution of various things. It's main use is to pause the script to let an animation finish before continuing."""
        self.buildmode = False
        ticks = None
        pri = 10000  #Will pause the script but nothing else
        for a in args:
            if a.startswith("priority="):
                pri = int(a[9:].strip())
            elif a=="all":
                pri = -1000
            elif a=="script":
                pri = 10000
            elif not ticks:
                ticks = float(a)
        if not ticks: ticks = 60
        do = delay(ticks)
        do.pri=pri
        self.obs.append(do)
    @category([
VALUE('ticks','How many ticks (1/60 of a second) before the command will be run'),
VALUE('command','The name of a macro to be run after the timer runs out')],type="gameflow")
    def _timer(self,command,ticks,run):
        """Schedule a macro to be executed after a certain amount of time. The rest of the game will proceed normally until the timer
        fires it's macro. Depending on what the macro does, the game may switch to a new mode or resume after the macro has
        completed."""
        self.obs.append(timer(int(ticks),run))
    @category([],type="gameflow")
    def _waitenter(self,command):
        """The script will pause until the user presses the enter key. Ok for demos but not recommended for real games, as
        it won't be obvious to users that they must press enter. gui Button or showing a normal textbox is preferred."""
        self.buildmode = False
        self.obs.append(waitenter())
    @category([],type="gameflow")
    def _exit(self,command):
        """Deletes the currently running scene/script from execution. If there are any scenes underneath, they will
        resume."""
        del assets.stack[-1]
    @category([VALUE("scene_name","Menu scene name. Scripts for each action should be named 'scene_name.examine.txt', 'scene_name.talk.txt', 'scene_name.present.txt', and 'scene_name.move.txt'"),
    KEYWORD('examine','whether to show the examine button','true'),
    KEYWORD('talk','whether to show the talk button','true'),
    KEYWORD('present','whether to show the present button','true'),
    KEYWORD('move','whether to show the move button','true')],type="interface")
    def _menu(self,command,ascene,*args):
        """Show an investigation menu of options. Should be run after the background of a scene is loaded. When an option
        is clicked, a separate script will be run for that action, as determined by the value of scene_name. When that
        external script is finished, the game won't return to this spot automatically, so you will need to be sure
        you can create the proper menu from the external screen as well. People usually do this by creating a script
        [scene_name].txt which loads the background and shows the menu. Then, any external script can
        instantly load the proper scene with "script [scene_name]". You can control which options
        are shown through the keywords described."""
        self.buildmode = False
        for o in self.obs:
            if o.__class__ in delete_on_menu:
                o.kill = 1
        m = menu()
        m.scene = ascene
        for scr in assets.list_casedir():
            if scr.startswith(m.scene+".") and scr not in [m.scene+".script.txt"]:
                m.addm(scr[scr.find(".")+1:scr.rfind(".")])
        for a in args:
            if "=" in a:
                arg,val = a.split("=")
                if not vtrue(val):
                    m.delm(arg)
        self.scriptlines = []
        self.si = 0
        self.obs.append(m)
        self.execute_macro("defaults")
        self.autosave()
    @category([KEYWORD('examine','whether to show the examine button','false'),
    KEYWORD('talk','whether to show the talk button','false'),
    KEYWORD('present','whether to show the present button','false'),
    KEYWORD('move','whether to show the move button','false'),
    KEYWORD('fail','label to jump to if the label for an action was not found','none')],type="interface")
    def _localmenu(self,command,*args):
        """Show an investigation menu of options. Should be run after the background of a scene is loaded. When an option
        is clicked, PyWright will jump to the label of the action, such as "label examine" or "label talk". You can control which options
        are shown through the keywords described."""
        self.buildmode = False
        for o in self.obs:
            if o.__class__ in delete_on_menu:
                o.kill = 1
        m = menu()
        for a in args:
            if "=" in a:
                arg,val = a.split("=")
                if arg=="fail":
                    m.fail = val
                elif vtrue(val):
                    m.addm(arg)
        m.open_script = False
        self.obs.append(m)
    @category([KEYWORD('pri','What priority to update the case menu','Default casemenu priority listed in core/sorting.txt')],type="interface")
    def _casemenu(self,command,*args):
        """Shows the phoenix wright styled case selection menu, allowing players to navigate available cases in a game folder
and choose one to play. The priority might need to be adjusted if you have any special animation going on, but don't modify it unless
you know you need it. This command should be the last command run from an intro.txt placed in a game's folder. PyWright will also
run the case menu by default if there is NO intro.txt in a game's folder. Single case games may opt to have the "case" folder and "game"
folder be the same, and not show a case menu at all."""
        self.buildmode = False
        kwargs = {}
        pri = ([x[4:] for x in args if x.startswith("pri=")] or [None])[0]
        if pri is not None: kwargs["pri"] = pri
        self.obs.append(case_menu(assets.game,**kwargs))
    @category(
    [VALUE('script_name',"name of the new script to load. Will look for 'script_name.script.txt', 'script_name.txt', or simple 'script_name', in the current case folder."),
KEYWORD('label','A label in the loading script to jump to after it loads.','Execution starts at the top of the script instead of a label'),
TOKEN('noclear','If this token is present, all the objects that exist will carry over into the new script.','Otherwise, the scene will be cleared.'),
TOKEN('stack','Puts the new script on top of the current script, instead of replacing it. When the new script exits, the current script will resume following this "script" command.','The new script will replace the current script.')],
type="gameflow")
    def _script(self,command,scriptname,*args):
        """Stops or pauses execution of the current script and loads a new script. If the token stack is included, then the current script will
resume when the new script exits, otherwise, the current script will vanish."""
        label = None
        for a in args:
            if a.startswith("label="):
                label = a.split("=",1)[1]
        if "noclear" not in args:
            for o in self.obs:
                o.kill = 1
        name = scriptname+".script"
        try:
            assets.open_script(name,False,".txt")
        except file_error:
            name = scriptname
        if "stack" in args:
            assets.addscene(name)
        else:
            p = self.parent
            self.init(name)
            self.parent = p
        while assets.cur_script.parent:
            parent = assets.cur_script.parent
            assets.cur_script.parent = parent.parent
            assets.stack.remove(parent)
        if label:
            self.goto_result(label,backup=None)
        self.execute_macro("defaults")
        self.autosave()
    @category([],type="logic")
    def _top(self,command):
        """Jumps to the top of the currently running script."""
        self.si = 0
    @category([VALUE("speed","The speed to set the selected animation to - this is the number of display frames to wait before showing the next animation frame."),
    KEYWORD("name","Only change the animation speed of objects with the given name","Change animation speed of all objects (if you want to mimic fastforward or slowdown you want to leave name= off)"),
    TOKEN("b","Select blinking animation for char objects"),
    TOKEN("t","Select talking animation for char objects")],type="animation")
    def _globaldelay(self,command,spd,*args):
        """Changes the default delay value for either all running animations or specific ones. First create the animation 
with a char, bg, fg, etc command, then call globaldelay to adjust the rate the animation will play. Use b or t to choose
blinking or talking animations if used with char. Normally, you will use the delay values stored with the animations themselves,
in the .txt files that go alongside the graphics. However, sometimes you may wish something to happen faster or slower."""
        name = None
        for a in args:
            if a.startswith("name="):
                name = a.split("=",1)[1]
        any = False
        for o in self.world.all:
            if name and getattr(o,"id_name",None)!=name:
                continue
            if isinstance(o,portrait):
                if "b" in args:
                    o = o.blink_sprite
                if "t" in args:
                    o = o.talk_sprite
            if hasattr(o,"spd"):
                o.spd = float(spd)
                any = True
        if name and not any and vtrue(assets.variables.get("_debug","false")):
            raise missing_object("No valid objects found by key name "+name)
    @category([KEYWORD("name","Named object to control","Will alter animation of all current objects - not recommended to use the default value."),
    KEYWORD("start","Alter the starting frame of the animation","Leave starting frame what it was."),
    KEYWORD("end","Alter ending frame of the animation","Leave ending frame what it was."),
    KEYWORD("jumpto","Instantly set an animations frame to this value","Don't change frames"),
    TOKEN("loop","Force animation to loop"),
    TOKEN("noloop","Force animation not to loop"),
    TOKEN("b","Alter blink animation of chars"),
    TOKEN("t","Alter talk animation of chars")],type="animation")
    def _controlanim(self,command,*args):
        """Alter the animation settings for a currently playing animated object. Normally you will use the settings that come with
the animation in the form of a .txt file next to the graphic file. Occasionally you may wish to play an animation differently, such
as having a non looping animation play several times, or only playing a portion of a longer animation."""
        start = None
        end = None
        name = None
        loop = None
        jumpto = None
        b = None
        t = None
        for a in args:
            if a.startswith("name="):
                name = a.split("=",1)[1]
            if a == "loop":
                loop = True
            if a == "noloop":
                loop = False
            if a.startswith("start="):
                start = int(a.split("=",1)[1])
            if a.startswith("end="):
                end = int(a.split("=",1)[1])
            if a.startswith("jumpto="):
                jumpto = int(a.split("=",1)[1])
            if a == "b":
                b = True
            elif a == "t":
                t = True
        any = False
        for o in self.world.all:
            if not name or getattr(o,"id_name",None)==name:
                any = True
                if isinstance(o,portrait):
                    if b:
                        o = o.blink_sprite
                    elif t:
                        o = o.talk_sprite
                if start is not None:
                    o.start = start
                    if o.x<start:
                        o.x = start
                if end is not None:
                    o.end = end
                if loop is not None:
                    if loop:
                        o.loops = 1
                    else:
                        o.loops = 0
                        o.loopmode = "stop"
                if jumpto is not None:
                    o.x = jumpto
        if name and not any and vtrue(assets.variables.get("_debug","false")):
            raise missing_object("No valid objects found by key name "+name)
    @category([VALUE("graphic_path","Path to the graphics file relative to case/art and without extension; such as bg/scene1 for games/mygame/mycase/art/bg/scene1.png and scene1.txt"),
KEYWORD("x","set the x value",0),
KEYWORD("y","set the y value",0),
KEYWORD("z","set the z value (check PyWright/core/sorting.txt for idea of z values)","sorting.txt lists default object z values"),
KEYWORD("loops","alter the loops of the object animation"),
TOKEN("flipx","Mirror the image on the x axis"),
KEYWORD("name","Gives the object a unique name to be used for other commands","Default name will be the graphic path"),
KEYWORD("rotz","rotate the object on the z axis",0),
TOKEN("fade","Object will fade in instead of popping in")],type="objects")
    def _obj(self,command,*args):
        """Creates a generic graphics object and places it in the scene. It will be drawn on a layer according to it's z value.
graphics objects may or may not be animated, which is defined in metadata files stored along with the graphics. ball.png will
have a ball.txt describing it's animation qualities, if it has any."""
        func = {"bg":bg,"fg":fg,"ev":evidence,"obj":graphic}[command]
        wait = {"fg":1}.get(command,0)
        clear = 1
        x = 0
        y = 0
        z = None
        loops = None
        fade = 0
        flipx = 0
        name = None
        more = {"rotx":0,"roty":0,"rotz":0}
        for a in args:
            if a.startswith("x="):
                x = int(a[2:])
            if a.startswith("y="):
                y = int(a[2:])
            if a.startswith("z="):
                z = int(a[2:])
            if a.startswith("loops="):
                loops = a[6:]
            if a=="flipx":
                flipx=1
            if a.startswith("name="):
                name = a[5:]
            if a.split("=")[0] in more.keys():
                more[str(a.split("=")[0])] = a.split("=")[1]
            if a=="stack":
                clear = 0
            if a=="nowait":
                wait = 0
        if y>=192 and assets.num_screens == 1 and assets.screen_compress:
            y -= 192
        more["wait"] = wait
        if clear and func==bg:
            for o in self.obs[:]:
                if getattr(o,"autoclear",False):
                    o.kill = 1
                    self.world.remove(o)
        o = func(args[0],x=x,y=y,flipx=flipx,**more)
        if z is not None:
            o.z = z
        if not fade:
            o.setfade(255)
        if name:
            o.id_name = name
        else:
            o.id_name = args[0]
        self.obs.append(o)
        if "fade" in args: self._fade("fade","wait","name="+o.id_name,"speed=5")
        if loops is not None:
            o.loops = int(loops)
        return o
    @category("blah")
    def _movie(self,command,file,sound=None):
        self.buildmode = False
        m = movie(file,sound)
        self.obs.append(m)
        return m
    @category([VALUE("bg_path","Path to the graphics file relative to case/art/bg and without extension; such as scene1 for games/mygame/mycase/art/bg/scene1.png and scene1.txt"),
KEYWORD("x","set the x value",0),
KEYWORD("y","set the y value",0),
KEYWORD("z","set the z value (check PyWright/core/sorting.txt for idea of z values)","sorting.txt lists default bg z values"),
KEYWORD("loops","alter the loops of the bg animation"),
TOKEN("flipx","Mirror the image on the x axis"),
KEYWORD("name","Gives the bg a unique name to be used for other commands","Default name will be the bg path"),
KEYWORD("rotz","rotate the object on the z axis",0),
TOKEN("stack","The scene won't be cleared when the background is loaded"),
TOKEN("fade","Background will fade in instead of popping in")],type="objects")
    def _bg(self,command,*args):
        """Creates a background object. If 'stack' is not included, the scene will be cleared before the background is loaded. Backgrounds also
default to a lower z value than other objects, ensuring that they will be in the background (though this can be modified). Other than that,
backgrounds have the same properties as other graphic objects, and may be animated or manipulated."""
        return self._obj(command,*args)
    @category([VALUE("fg_path","Path to the graphics file relative to case/art/fg and without extension; such as fence for games/mygame/mycase/art/fg/fence.png and fence.txt"),
KEYWORD("x","set the x value",0),
KEYWORD("y","set the y value",0),
KEYWORD("z","set the z value (check PyWright/core/sorting.txt for idea of z values)","sorting.txt lists default fg z values"),
KEYWORD("loops","alter the loops of the fg animation"),
TOKEN("flipx","Mirror the image on the x axis"),
KEYWORD("name","Gives the fg object a unique name to be used for other commands","Default name will be the fg path"),
KEYWORD("rotz","rotate the object on the z axis",0),
TOKEN("nowait","Continue game execution without waiting for foreground animation to finish."),
TOKEN("fade","Object will fade in instead of popping in")],type="objects")
    def _fg(self,command,*args):
        """Creates a foreground object. These are just like any other object, except the default z value will place them in front of most of the
objects in the scene."""
        return self._obj(command,*args)
    @category([VALUE("evidencekey","Evidence id key. PyWright will look at the 'evidencekey_pic' variable to determine what graphic file to load"),
KEYWORD("x","set the x value",0),
KEYWORD("y","set the y value",0),
KEYWORD("z","set the z value (check PyWright/core/sorting.txt for idea of z values)","sorting.txt lists default ev z values"),
KEYWORD("loops","alter the loops of the animation"),
TOKEN("flipx","Mirror the image on the x axis"),
KEYWORD("name","Gives the object a unique name to be used for other commands","Default name will be the evidence key"),
KEYWORD("rotz","rotate the object on the z axis",0),
TOKEN("fade","Object will fade in instead of popping in")],type="objects")
    def _ev(self,command,*args):
        """Creates a graphic for an evidence key. The graphic is based on whatever you set for that specific evidence key. You can easily
add an item to the court record and then display the same item on screen. Example:
{{{set housekey_pic key1
set housekey_name House Key
set housekey_desc The key to the victim's house
addev housekey
ev housekey
"House key added to court record"
}}}"""
        self._obj(command,*args)
    @category([VALUE("character_name","Name of character folder in art/port. If the character is to be hidden, the character_name doesn't need to match up to any actual directory. Graphics will be loaded from that directory according to the visible emotion"),
KEYWORD("nametag","The name to actually display to the player as this character's name.","character_name"),
KEYWORD("e","The character's starting emotion","normal"),
KEYWORD("be","The emotion to use while character is in the blink pose"),
KEYWORD("x","set the x value","default x places character in the center of the screen"),
KEYWORD("y","set the y value","default y places the bottom of the character graphic at the bottom of the screen"),
KEYWORD("z","set the z value (check PyWright/core/sorting.txt for idea of z values)","sorting.txt lists default char z values"),
KEYWORD("name","Gives the object a unique name to be used for other commands","Default name will be character_name"),
KEYWORD("pri","Alter the default priority of the character animation","sorting.txt lists default pri values"),
TOKEN("fade","Character will fade in instead of popping in"),
TOKEN("stack","Don't delete other characters before adding this one","All other characters are deleted"),
TOKEN("hide","Don't actually show the character, just set who is talking"),
TOKEN("noauto","Just play the animation, don't let textboxes set talk/blink modes or do lip syncing.")],type="objects")
    def _char(self,command,character="",*args):
        """Create a character object, and set that object as the currently speaking character. (The variable _speaking_name contains
the object name of the currently speaking character). Character's in pywright refer to a folder containing various animations belonging
to the character. This "emotion" can be set with the e= keyword on the char command, as well as modified during text. Textboxes
also will control the animation of the currently speaking character to make the mouth movements match the speed the text is
printing."""
        assets.character = character
        z = None
        e = "normal(blink)"
        be = ""
        x = 0
        y = 0
        pri = None
        name = None
        nametag = character+u"\n"
        for a in args:
            if a.startswith("z="): z = int(a[2:])
            if a.startswith("e="): e = a[2:]+"(blink)"
            if a.startswith("be="): be = a[3:]
            if a.startswith("x="): x = int(a[2:])
            if a.startswith("y="): y = int(a[2:])
            if a.startswith("priority="): pri = int(a[9:])
            if a.startswith("name="): name = a[5:]
            if a.startswith("nametag="): nametag = a[8:]+u"\n"
        assets.px = x
        assets.py = y
        assets.pz = z
        p = assets.add_portrait(character+"/"+e,fade=("fade" in args),stack=("stack" in args),hide=("hide" in args))
        if pri:
            p.pri = pri
        if name:
            p.id_name = name
        else:
            p.id_name = character
        p.nametag = nametag
        if "fade" in args: 
            self._fade("fade","wait","name="+p.id_name,"speed=5")
            p.extrastr = " fade"
        assets.variables["_speaking_name"] = nametag
        if be:
            p.set_blink_emotion(be)
        p.single = "noauto" in args
        return p
    @category([VALUE("emotion","Emotion animation to set character to"),VALUE("name","Object name of character to change emotion of","Chooses currently speaking character (value of _speaking_name)")],type="objects")
    def _emo(self,command,emotion,name=None,mode="talk"):
        """Sets a current char object to a specific emotion animation."""
        char = None
        if not name:
            char = assets.variables.get("_speaking", None)
        if name:
            for c in self.obs:
                if isinstance(c,portrait) and getattr(c,"id_name",None)==name.split("=",1)[1]:
                    char = c
                    break
            if not char and vtrue(assets.variables.get("_debug","false")):
                raise missing_object(command+": No character found by key name "+name)
        if char:
            nametag = char.nametag
            if mode == 'talk':
                char.set_emotion(emotion)
            elif mode == 'blink':
                char.set_blink_emotion(emotion)
            char.nametag = nametag
            assets.variables["_speaking_name"] = nametag
        elif vtrue(assets.variables.get("_debug","false")):
            raise missing_object(command+": No character found to set emotion!")
    @category([VALUE("emotion","Blinking emotion animation to set character to"),VALUE("name","Object name of character to change blinking emotion of","Chooses currently speaking character (value of _speaking_name)")],type="objects")
    def _bemo(self,command,emotion,name=None):
        """Sets a current char object to a specific blinking emotion animation."""
        self._emo("bemo",emotion,name,"blink")
    @category([VALUE('type','type of gui to create. (Back, Button, Input, or Wait)'),
VALUE('macro','First argument after Button is the name of the macro to run when the button is pressed, valid for (Button)'),
VALUE('var_name','Variable name to save input text into, valid for (Input)'),
KEYWORD('x','x position of created item, valid for (Back, Button, Input)'),
KEYWORD('y','y position of created item, valid for (Back, Button, Input)'),
KEYWORD('z', 'z position of created item, valid for (Back, Button, Input)'),
KEYWORD('width','pixel width of input box, valid for (Input)'),
KEYWORD('name','id to give object for later reference, valid for (Back, Button, Input)'),
KEYWORD('graphic','path to graphic file, valid for (Button)','default for buttons is to have an outline with the text of the button label'),
TOKEN('hold','hold means that the macro will repeatedly execute as long as the button is held down, valid for (Button)','default is that it only executes with each distinct click'),
TOKEN('password','typed text will be displayed with stars *****, valid for (Input)','default is to show text'),
KEYWORD('run','repeatedly execute this macro, valid for (Wait)','default is no macro will be run'),
COMBINED('text','remaining text will display for Button if there is no graphic, valid for (Button)','default is no text')],type="interface")
    def _gui(self,command,guitype,*args):
        """This complex command is used to build custom interfaces and behavior into your game. If you don't understand it you probably
don't need to use it, but if you are doing something that isn't quite standard you will probably need this command at one time or another.
The four types of gui you can create are:

* Button - This creates a button that can be clicked. When clicked a macro will run.
* Back - This is a specialized button which displays the PyWright back button. The game will halt until the back button is pressed, making it pretty easy to create a custom screen for evidence
* Input - this will show an input box allowing the player to input text. This text will be saved into a variable which you define.
* Wait - this command will pause the script and optionally execute a macro each frame
"""
        args = list(args)
        x=None
        y=None
        z=None
        width=None
        height=None
        name=""
        if guitype=="Back":
            while args:
                a = args.pop(0)
                if a.startswith("x="): x=int(a[2:])
                elif a.startswith("y="): y=int(a[2:])
                elif a.startswith("z="): z=int(a[2:])
                elif a.startswith("name="): name=a[5:]
            if y>=192 and assets.num_screens == 1 and assets.screen_compress:
                y -= 192
            self.obs.append(guiBack(x=x,y=y,z=z,name=name))
            self.buildmode = False
        if guitype=="Button":
            macroname=args[0]; del args[0]
            graphic = None
            hold = None
            while args:
                a = args[0]
                print a
                if a.startswith("x="): x=int(a[2:])
                elif a.startswith("y="): y=int(a[2:])
                elif a.startswith("z="): z=int(a[2:])
                elif a.startswith("name="): name=a[5:]
                elif a.startswith("graphic="): graphic = a[8:]
                elif a == "hold": hold = True
                else:
                    break
                del args[0]
            text = ""
            text = " ".join(args)
            btn = gui.button(None,text)
            btn.s_text = text
            if graphic:
                btn.s_graphic = graphic
                graphic = assets.open_art(graphic)[0]
            btn.graphic = graphic
            if y>=192 and assets.num_screens == 1 and assets.screen_compress:
                y -= 192
            btn.rpos = [x,y]
            btn.z = int(assets.variables["_layer_gui"])
            if z is not None: btn.z = z
            btn.pri = 0
            btn.s_macroname = macroname
            def func(*args):
                self.goto_result(macroname)
            setattr(btn,text.replace(" ","_"),func)
            if hold:
                btn.z=10000
                btn.hold_down_over = func
            self.obs.append(btn)
            if name: btn.id_name = name
            else: btn.id_name = "$$"+str(id(btn))+"$$"
        if guitype=="Input":
            varname=args[0]; del args[0]
            varvalue = assets.variables.get(varname,"")
            assets.variables[varname] = varvalue
            #graphic = None
            type = "normal"
            while args:
                a = args.pop(0)
                if a.startswith("x="): x=int(a[2:])
                elif a.startswith("y="): y=int(a[2:])
                elif a.startswith("z="): z=int(a[2:])
                elif a.startswith("name="): name=a[5:]
                elif a.startswith("width="): width=int(a[6:])
                #elif a.startswith("graphic="): graphic = args[0][8:]
                elif a == "password":
                    type = "password"
            eb = gui.editbox(assets.variables,varname,is_dict=True)
            #~ if graphic:
                #~ btn.s_graphic = graphic
                #~ graphic = assets.open_art(graphic)[0]
            #~ btn.graphic = graphic
            if y>=192 and assets.num_screens == 1 and assets.screen_compress:
                y -= 192
            eb.rpos = [x,y]
            if width:
                eb.force_width = width
            eb.z = int(assets.variables["_layer_gui"])
            if z is not None: eb.z = z
            eb.pri = 0
            if name: eb.id_name = name
            else: eb.id_name = "$$"+str(id(eb))+"$$"
            self.obs.append(eb)
        if guitype=="Wait":
            run = ""
            if args and args[0].startswith("run="): run = args[0].replace("run=","",1)
            self.obs.append(guiWait(run=run))
            self.buildmode = False
    @category([VALUE('x','x value to place text'),VALUE('y','y value to place text'),VALUE('width','width of text block'),
    VALUE('height','height of text block (determines rows but the value is in pixels)'),
    KEYWORD('color','color of the text'),
    KEYWORD('name','id of textblock object for later reference'),
    COMBINED('text','text to display')],type='text')
    def _textblock(self,command,x,y,width,height,*text):
        """Displays a block of text all at once on the screen somewhere. Used to create custom interfaces. The text doesn't
        support markup in the same way that textboxes do."""
        id_name = None
        color = None
        if text and text[0].startswith("color="):
            color = color_str(text[0][6:])
            text = text[1:]
        if text and text[0].startswith("name="): 
            id_name = text[0].replace("name=","",1)
            text = text[1:]
        y = int(y)
        if y>=192 and assets.num_screens == 1 and assets.screen_compress:
            y -= 192
        tb = textblock(" ".join(text),[int(x),int(y)],[int(width),int(height)],surf=pygame.screen)
        self.obs.append(tb)
        if id_name: tb.id_name = id_name
        else: tb.id_name = "$$"+str(id(tb))+"$$"
        if color:
            tb.color = color
    @category([VALUE("change_amount","Amount of health to change, either adding, subtracting, or setting the health, while animating the change on the bar","By default there will be no change"),
    KEYWORD("variable","the health variable to use",'"penalty"'),
    KEYWORD("threat","Amount of health to threaten the player with losing (flashes this portion of the bar)","0"),
    KEYWORD("delay","How long to delay the script before deleting the bar and continuing. A value of 0 means no delay and the bar will stay onscreen until deleted.","Default is 50 if the value is changing, and 0 if the value is not")],type="objects")
    def _penalty(self,command,*args):
        """Display a health bar, and if change_amount is given, show the player that they are losing health, 
        and subtract the health. If change_amount starts with a minus sign, the amount will be subtracted from
        the current health value. If it starts with a plus sign, the amount will be added to the current health value.
        With no minus or plus sign, it will SET the health value to this amount, but still animate the change. At 
        your game's checkpoints, you will probably want "penalty 100", which will show the healthbar
        filling up to that amount.
        
        Without change_amount, you are just showing the player their current health, and optionally threatening
        them with an amount they may lose if they make the wrong choice.
        
        There is support for multiple health variables, if you were to have a multiple
        character game, or maybe you want to keep score and have a new health bar in each case. The 'variable'
        keyword allows you to choose which health bar the penalty command is referring to.
        
        Since it just uses variables, you can also change the health bar values behind the scenes without showing
        the penalty bar at all, by just using the normal variable commands. The default penalty variable is 'penalty'."""
        var = "penalty"
        flash_amount = 0
        delay = None
        args = list(args)
        for a in args[:]:
            if a.split("=")[0] == "variable":
                var = a.split("=",1)[1]
                args.remove(a)
            if a.split("=")[0] == "threat":
                flash_amount = int(a.split("=",1)[1])
                args.remove(a)
            if a.split("=")[0] == "delay":
                delay = int(a.split("=",1)[1])
                args.remove(a)
        amt = "NONE"
        if args:
            amt = args[0]
        if not delay:
            delay = 50
            if amt=="NONE" or flash_amount:
                delay = 0
        if amt=="NONE":
            end = int(assets.variables.get(var,100))
        elif not amt.isdigit():
            end = int(assets.variables.get(var,100))+int(amt)
        else:
            end = int(amt)
        pen = penalty(end,var,flash_amount=flash_amount)
        pen.delay = delay
        self.obs.append(pen)
        self.buildmode = False
    @category([KEYWORD("degrees","How many degrees to rotate"),KEYWORD("speed","How many degrees to rotate per frame"),
    KEYWORD("axis","which axis to rotate on, z is the only valid value","z"),
    KEYWORD("name","Name a specific object to rotate","Will try to rotate all objects (not what you might expect)"),
    TOKEN("nowait","Continue script while rotation happens","The script will pause until rotation is finished")],type="effect")
    def _rotate(self,command,*args):
        """Begins an object rotation animation. Will wait for rotation to finish unless
        'nowait' is included."""
        kwargs,args = parseargs(args,intvals=["degrees","speed","wait"],
                                                defaults={"axis":"z",'wait':1},
                                                setzero={"nowait":"wait"})
        self.obs.append(rotateanim(obs=self.obs,**kwargs))
        if kwargs['wait']: self.buildmode = False
    @category([KEYWORD("start","What fade level to start at",0),
    KEYWORD("end","What fade level to end at",100),
    KEYWORD("speed","How many fade steps per frame",1),
    KEYWORD("name","Name a specific object to fade","Will try to fade all objects"),
    TOKEN("nowait","Continue script while fade happens","The script will pause until fade is finished")],type="effect")
    def _fade(self,command,*args):
        """Fade an object or objects in or out"""
        kwargs,args = parseargs(args,intvals=["start","end","speed","wait"],
                                                defaults={"start":0,"end":100,"speed":1,"wait":1},
                                                setzero={"nowait":"wait"})
        self.obs.append(fadeanim(obs=self.obs,**kwargs))
        if kwargs['wait']: self.buildmode = False
    @category([KEYWORD("start","Color tint to start at","'ffffff' or no tint (full color)"),
    KEYWORD("end","Color tint to end at","'000000' or full black tint"),
    KEYWORD("speed","How many color steps per frame",1),
    KEYWORD("name","Name a specific object to tint","Will try to tint all objects"),
    TOKEN("nowait","Continue script while fade happens","The script will pause until fade is finished")],type="effect")
    def _tint(self,command,*args):
        """Animate an object's tint from one color to another. You can make an object darker but not brighter. Tinting an object
        to red subtly can make a blush effect, tinting objects darker if there is a cloud overhead, or mixing tint with greyscale
        to make a sepia toned flashback scene are different ways this can be used."""
        kwargs,args = parseargs(args,intvals=["speed","wait"],
                                                defaults={"start":"ffffff","end":"000000","speed":1,"wait":1},
                                                setzero={"nowait":"wait"})
        self.obs.append(tintanim(obs=self.obs,**kwargs))
        if kwargs['wait']: self.buildmode = False
    @category([KEYWORD("value","Whether an object should be inverted or not: 1=inverted 0=not","1"),
    KEYWORD("name","Name a specific object to tint","Will try to tint all objects")],type="effect")
    def _invert(self,command,*args):
        """Invert the colors of an object."""
        kwargs,args = parseargs(args,intvals=["value"],
                                                defaults={"value":1,"name":None})
        kwargs["start"] = 1-kwargs["value"]
        kwargs["end"] = kwargs["value"]
        self.obs.append(invertanim(obs=self.obs,**kwargs))
    @category([KEYWORD("value","Whether an object should be greyscale or not: 1=greyscale 0=not","1"),
    KEYWORD("name","Name a specific object to set to greyscale","Will try to greyscale all objects")],type="effect")
    def _grey(self,command,*args):
        """Makes an object display in greyscale."""
        kwargs,args = parseargs(args,intvals=["value"],
                                                defaults={"value":1,"name":None})
        kwargs["start"] = 1-kwargs["value"]
        kwargs["end"] = kwargs["value"]
        self.obs.append(greyscaleanim(obs=self.obs,**kwargs))
    @category([VALUE("ttl","Time for shake to last in frames","30"),
    VALUE("offset","How many pixels away to move the screen (how violent)","15"),
    TOKEN("nowait","Continue executing script during shake")],type="effect")
    def _shake(self,command,*args):
        """Shake the screen for effect."""
        args = list(args)
        ttl = 30
        offset = 15
        wait = True
        if "nowait" in args:
            wait = False
            args.remove("nowait")
        if len(args)>0:
            ttl = int(args[0])
        if len(args)>1:
            offset = int(args[1])
        sh = shake()
        sh.ttl = ttl
        sh.offset = offset
        sh.wait = wait
        self.obs.append(sh)
    @category([KEYWORD("mag","How many times to magnify","1 (will magnify 1 time, which is 2x magnification)"),
    KEYWORD("frames","how many frames for the zoom to take","1"),
    KEYWORD("name","Which object to magnify","tries to magnify everything"),
    TOKEN("nowait","continue script during magnification"),
    TOKEN("last","Choose last added object as target")],type="effect")
    def _zoom(self,command,*args):
        """Causes a single object or all objects to be magnified. The value for 'mag' will be added to the current magnification
        value of an object, and it will take 'frames' frames to get to the new value. By default, all objects are at a magnification
        of 1. To shrink an object to half it's size for instance, you would use this command:
{{{
zoom mag=-0.5 frames=10
}}}
        This will subtract half magnification from an object over 10 frames: 1x - 0.5x = 0.5x."""
        mag = 1
        frames = 1
        wait = 1
        last = 0
        name = None
        filter = "top"
        for a in args:
            if a.startswith("mag="):
                mag=float(a[4:])
            if a.startswith("frames="):
                frames=int(a[7:])
            if a.startswith("last"):
                last = 1
            if a.startswith("nowait"):
                wait = 0
            if a.startswith("name="):
                name = a[5:]
        zzzooom = zoomanim(mag,frames,wait,name)
        if last:
            zzzooom.control_last()
        if name:
            zzzooom.control(name)
        self.obs.append(zzzooom)
        if wait: self.buildmode = False
    @category([KEYWORD("name","Name of object to scroll","scrolls everything"),
    KEYWORD("filter","select only objects on the 'top' screen or 'bottom' screen, leave blank for either","'top'"),
    KEYWORD("x","amount to scroll horizontally","0"),
    KEYWORD("y","amount to scroll vertically","0"),
    KEYWORD("speed","pixels per frame to scroll","1"),
    TOKEN("last","select last added object as scroll target"),
    TOKEN("nowait","continue script while scrolling")],type="effect")
    def _scroll(self,command,*args):
        """Scrolls the screen around, can also be used to move individual objects. Positive values for x will move objects LEFT 
(consider moving the viewpoint/camera RIGHT) and positive values for y will move objects UP (moving the viewpoint/camera DOWN) If the
scroll amount does not divide evenly by the speed, it will still stop at the right place. (In older versions you needed to make sure
the speed would divide evenly over the distance)."""
        x=0
        y=0
        speed = 1
        last = 0
        wait = 1
        name = None
        filter = "top"
        for a in args:
            if a.startswith("x="):
                x=int(a[2:])
            if a.startswith("y="):
                y=int(a[2:])
            if a.startswith("speed="):
                speed=int(a[6:])
            if a.startswith("last"):
                last = 1
            if a.startswith("nowait"):
                wait = 0
            if a.startswith("name="):
                name = a[5:]
            if a.startswith("filter="):
                filter=a[7:]
        scr = scroll(x,y,speed,wait,filter)
        self.obs.append(scr)
        if last:
            scr.control_last()
        if name:
            scr.control(name)
        if wait: self.buildmode = False
    @category([COMBINED("filename","Filename of song, searches game/case/music, game/music, and PyWright/music","If no path is listed, music will stop")],type="music")
    def _mus(self,command,*song):
        """Stops currently playing music file, and if 'filename' is given, starts playing a new one. If you want to queue up a song to play when the current
        song is finished, used for situations where you want an intro to a looping track, run this code anytime after the mus command: {{{set _music_loop track_name}}}.
        
        Songs can be .ogg, .mod, .it, .mid, .xm, .s3m, or uncompressed .wav"""
        track = " ".join(song)
        if not track:
            assets.stop_music()
        else:
            assets.play_music(track)
    @category([COMBINED("filename","Filename of sound file, searches game/case/sfx, game/sfx, and PyWright/sfx"),
    KEYWORD("after","Delay sound for this many frames")],type="sounds")
    def _sfx(self,command,*sound):
        """Play a sound effect. If 'after' will play the sound after a certain number of frames (useful to time an effect with a specific
        frame of an animation).
        
        Sound files can be .ogg or uncompressed .wav"""
        after = 0
        if sound and sound[0].startswith("after="):
            after = float(sound[0].replace("after=","",1))
            sound = sound[1:]
        sound = " ".join(sound)
        self.obs.append(SoundEvent(sound,after))
    @category([COMBINED("nametag","Text to set for the next nametag","If no text is given, the next nametag will be invisible")],type="text")
    def _nt(self,command,*name):
        """Sets or clears the next nametag. Must be called immediately before the textbox it alters. Other commands like "char" or "set _speaking" which alter the
        nametag may conflict with this command."""
        nametag = " ".join(name)+"\n"
        assets.variables["_speaking"] = ""
        assets.variables["_speaking_name"] = nametag
    @category([VALUE("tag","Name of evidence to add to the court record"),VALUE("page","Which page to add evidence to","Default is to add to the evidence page, unless the tag ends with a '$' in which case it will add to profiles")],type="evidence")
    def _addev(self,command,ev,page=None):
        """Adds evidence to the court record based on an evidence 'tag'. The various properties of the evidence should be stored in variables based on this tag:

set [tag]_name: the name displayed to the player on court record screen for this item, defaults to the tag itself

set [tag]_pic: the image to use, should be in game/case/art/ev, or game/art/ev, defaults to the tag ([tag].png in art/ev)

set [tag]_desc: the long description of the evidence, shown on zoomed court record view, defaults to blank

set [tag]_check: name of a script to run if item is checked by player"""
        evob = evidence(ev,page=page)
        if ev not in [x.id for x in assets.items]: assets.items.append(evob)
    @category([VALUE("tag","name of evidence to delete from court record")],type="evidence")
    def _delev(self,command,ev):
        """Delete an item from the court record."""
        ids = [x.id for x in assets.items]
        if ev in ids: del assets.items[ids.index(ev)]
    @category([VALUE("tag","Tag this list with some name so PyWright can keep track of which list options the player has tried already","Default is to name the list based on what script it's found in and on what line")],type="interface")
    def _list(self,command,tag=None):
        """Start building a list of options to present the player. By default, each list will be unique. If you have a list appear in multiple parts of the code, but
        they are meant to appear to the player as the same list, make sure they have the same tag. Also, the tag you give will do double duty, as you can use
        'goto [tag]' to jump straight to the list without any other labels. To actually build the list requires a series of 'li' commands, and then displaying the list 
        will require the command 'showlist'. Upon choosing an option, PyWright will try to jump to a label matching the text of the option. Example below, more info
        under 'li' and 'showlist'.
{{{
"What is your favorite food?"

list faveorite_food
li hamburger
li HAMBURGER
li hamburger?
showlist

label hamburger
"Wow you like hamburgers too?"
exit

label HAMBURGER
"Gee, you don't have to be so grumpy about it."
exit

label hamburger?
"Yes, that is correct. Don't be timid."
exit}}}
"""
        if tag:
            assets.lists[tag] = assets.lists.get(tag,{})
        self.obs.append(listmenu(tag))
    @category([COMBINED("option","text to display, and if 'result' not given, label to jump to if option is selected"),
    KEYWORD('result','specifically named label to jump to if this option is chosen')],type="interface")
    def _li(self,command,*label):
        """Add an item to the current list. When clicked, PyWright will go to a label either matching the option text, or matching the value of 'result'
        if that was given. Must be used between 'list' and 'showlist' commands."""
        if label[-1].startswith("result="):
            result = label[-1][7:]
            label = " ".join(label[:-1])
        else:
            label=result=" ".join(label)
        for o in self.obs:
            if isinstance(o,listmenu):
                o.options.append([label,result])
    @category([],type="interface")
    def _showlist(self,command,*args):
        """Finish building a list and display it to the user, waiting for the user to choose a list option before script resumes. Must follow 'list' and
        a series of 'li' commands."""
        fail = None
        for a in args:
            if "=" in a:
                k,v = a.split("=",1)
                if k == "fail":
                    fail = v
        for o in self.obs:
            if isinstance(o,listmenu):
                o.hidden = False
                if fail:
                    o.fail = fail
        self.buildmode = False
    @category([VALUE("tag","list tag to forget")],type="gameflow")
    def _forgetlist(self,command,tag):
        """Clears the memory of which options player has chosen from a specific list. Normally, chosen options from a list
        will be shown with a checkmark to remind the player which options they have tried, and which ones are new. You
        can make all the options for a list not show checkmarks by clearing the memory."""
        if tag in assets.lists:
            del assets.lists[tag]
    @category([VALUE("tag","list to forget item from"),COMBINED("option","option from list to forget state of")],type="gameflow")
    def _forgetlistitem(self,command,tag,*item):
        """Forget checkmark status of a specific option from a specific list."""
        if tag in assets.lists:
            if item in assets.lists[tag]:
                del assets.lists[tag][" ".join(item)]
    @category([],type="objects")
    def _clear(self,command):
        """Clears all objects from the scene."""
        for o in self.obs:
            o.kill = 1
        pygame.screen.fill([0,0,0])
    @category([KEYWORD("name","Unique name of object to delete.")],type="objects")
    def _delete(self,command,*args):
        """Deletes the named object from the scene. (Any time you give an object a name, such as 'ev bloody_knife name=bk' you can
        use this command to delete it later, such as 'delete name=bk'."""
        name = None
        for a in args:
            if a.startswith("name="):
                name = a[5:]
        any = False
        for o in reversed(self.obs):
            if getattr(o,"id_name",None)==name:
                any = True
                o.kill = 1
                break
        if name and not any and vtrue(assets.variables.get("_debug","false")):
            raise missing_object("Delete: cannot find "+name+" (might not be a problem, often delete is used just in case some object is still around)")
    @category([KEYWORD("fail","label to jump to when a specific evidence label is not found.","none")],type="interface")
    def _present(self,command,*args):
        """Displays the court record and allows the player to present evidence. After the presentation,
        will jump to the label named after the selected evidence tag. If a label for the chosen evidence
        is not found, will either jump to 'label none', or the value of 'fail'."""
        self.statement = ""
        self.cross = "proceed"
        ob = evidence_menu(assets.items)
        for a in args:
            if "=" in a:
                k,v = a.split("=",1)
                if k == "fail":
                    ob.fail = v
        addob(ob)
        self.buildmode = False
    @category([KEYWORD("fail","label to jump to when a specific evidence label is not found.","none")],type="interface")
    def _examine(self,command,*args):
        """Displays the examine cursor to allow the player to choose a spot on the screen, and jump to different labels
        based on the spot. Immediately following the examine command, you must use region commands to define where the
        player can click."""
        em = examine_menu(hide=("hide" in args),name=self.scene+":%s"%self.si)
        self.obs.append(em)
        while self.si<len(self.scriptlines):
            line = self.getline()
            if line is None: return
            if not line.strip(): 
                self.si+=1
                continue
            if not line.startswith("region "):
                self.si+=1
                break
            em.addregion(*line.replace("region ","").strip().split(" "))
            self.si+=1
        self.si-=1
        self.buildmode = False
        for a in args:
            if "=" in a:
                k,v = a.split("=",1)
                if k == "fail":
                    em.fail = v
    @category([VALUE("label","label the cross exam so that you can 'goto label' later to start from the top"),
    KEYWORD("fail","label to jump to if no label is defined for an action, when pressing or presenting",'"none"')],type="crossexam")
    def _cross(self,command,*args):
        """Begin a cross examination. You may tag this cross examination, such as 'cross testimony1' which will
allow you to jump to the beginning of the testimony again with 'goto testimony1'. Aftter the 'cross' line,
you will have a series of 'statement's which define each line of text that the witness says which make up the testimony.
When statements are finished, you will have the line 'endcross' which signifies that responses for player action
during the testimony, in the form of 'label's, will follow.

General layout of a cross examination:
{{{cross [label]
statement [statement tag]
[text]
statement [statement tag]
[text]
statement [statement tag]
endcross

[defense and helper discussing about difficuly]
goto [label]

[label for user action]
[text]
resume

[label for another user action]
[text]
resume

[label for successful user action (probably a present)]
[text]
goto continue

label none
[general text for a bad present]
resume

label continue
[rest of game]}}}

See <statement> for more info on hiding and revealing statements. Also, <endcross>.
<resume> has a special use for cross examinations, in that it will jump back to the next statement
the user was on, after handling logic outside of cross/endcross. It is better to use 'resume' than
'goto top' or 'goto [label]', which will restart the cross examination from the beginning. It's especially
useful to use 'resume' in the 'fail' case, because you won't know where the player came from."""
        assets.variables["_court_fail_label"] = "none"
        self.statement = ""
        for a in args:
            if "=" in a:
                k,v = a.split("=",1)
                if k == "fail":
                    assets.variables["_court_fail_label"] = v
        if self.cross is None:
            self.cross = self.si
        else:
            if self.cross != "proceed":
                self.cross = "proceed"
        assets.variables["currentcross"] = self.si
        assets.variables["_statements"] = []
        for ni,line in enumerate(self.scriptlines[self.si:]):
            if line.startswith("statement "):
                statement,test = self.parse_statement(line.split(" ")[1:])
                assets.variables["_statements"].append({"words":statement,"test":test,"index":self.si+ni})
            if line.startswith("endcross"):
                #Add a dummy last statement so that next_statement can exit the cross/endcross section
                assets.variables["_statements"].append({"words":"$$$","test":None,"index":self.si+ni})
                break
    @category([],type="crossexam")
    def _cross_restart(self,command,*args):
        """Go to the first line in the current cross examination"""
        if assets.variables.get("currentcross",None) is not None:
            self.si = assets.variables.get("currentcross",None)
    @category([],type="crossexam")
    def _next_statement(self,command,*args):
        """Go to the next statement, usually not needed (the user is usually in control of navigating statements)"""
        self.next_statement()
    @category([],type="crossexam")
    def _prev_statement(self,command,*args):
        """Go to the previous statement, usually not needed (the user is usually in control of navigating statements)"""
        self.prev_statement()
    @category([],type="crossexam")
    def _endcross(self,command):
        """End the current cross examination section. Usually followed by labels for responding to user action.
        See <cross> and <statement> for more info on cross examinations."""
        self.statement = ""
        self.cross = None
    def parse_statement(self,statement):
        test = None
        statement = list(statement)
        if statement[-1].startswith("test="):
            test = statement.pop(-1)[5:]
        statement = " ".join(statement)
        return statement,test
    @category([COMBINED("tag","Name the statement so you can match up user action results with it"),
    KEYWORD("test","Name of a variable. Only show this statement if that variable is true.","all statements shown by default")],type="crossexam")
    def _statement(self,command,*statement):
        """Must be between 'cross' and 'endcross'. Defines a specific statement within a witness testimony for 
        cross examination. Usually followed by a line of text spoken by the witness. The 'tag' will be refered to by labels
        which follow the 'endcross' of this cross examination (although it is also possible to put the response label
        immediately following the line of text).
        
        label press [tag] - PyWright will jump to a label that looks like this if the user "presses" this statement
        
        label [evidence_tag] [tag] - PyWright will jump to this label when the user presents this evidence to this statement
        
        If no matching label is found, PyWright will jump to the value of 'fail=' given to '<cross>'."""
        statement,test = self.parse_statement(statement)
        if not self.state_test_true(test):
            self.next_statement()
            return
        self.instatement = True
        self.statement = statement
        self.cross = "proceed"
    @category([],type="logic")
    def _resume(self,command):
        """Returns to the next line after a jump. Also, in cross examinations, will
        return the the proper statement.
        
        Example:
        {{{"This is just a test. Jumping elsewhere in the code..."
        goto test
        "And now we are back."
        
        label test
        "Here we have jumped, but now we go back..."
        resume}}}
        
        This will print:
        {{{
        "This is just a test. Jumping elsewhere in the code..."
        "Here we have jumped, but now we go back..."
        "And now we are back."}}}"""
        if self.statement:
            for x in assets.variables["_statements"]:
                if x["words"]==self.statement:
                    self.si = x["index"]
                    self.next_statement()
            self.cross = "proceed"
            return
        self.si = self.lastline
    @category([],type="crossexam")
    def _clearcross(self,command):
        """Clears all cross exam related variables. A good idea to call this after a testimony
        is officially over, to ensure that 'resumes' don't mistakenly go back to the cross exam, 
        and prevent other bugs from occuring."""
        self.cross = None
        self.lastline = 0
        self.statement = ""
        self.instatement = False
    @category([VALUE("filename","file to write to"),
    COMBINED("text","text to write")],type="files")
    def _filewrite(self,command,filename,*text):
        """Writes text to the end of the specified file. Text is immediately flushed, files written to in
        this way do not need to be explicitly "saved". Use "\n" for carriage return in the file, "\t" for tab
        characters. 'filename' cannot contain spaces or be located earlier than the current game on the path.
        
        See <fileclear> and <fileseek> for other file commands."""
        f = open(filename,"ab")
        f.write(text)
        f.flush()
        
assets.Script = Script

class DebugScript(Script):
    def __init__(self):
        super(DebugScript,self).__init__()
        self.char_cache = {}
    def update_objects(self):
        #~ for o in self.obs:
            #~ if isinstance(o,textbox):
                #~ for i in range(400):
                    #~ o.update()
                #~ o.forward()
            #~ else:
                #~ o.update()
        [x.update() for x in self.obs]
        return True
    def call_func(self,command,args):
        if command in ["set","setvar"]:
            super(DebugScript,self).call_func(command,args)
        if command == "char":
            if "hide" in args:
                return
            if "stack" not in args:
                for o in self.obs:
                    if isinstance(o,portrait):
                        o.kill = 1
            if tuple(args) in self.char_cache:
                c = self.char_cache[tuple(args)]
                self.obs.append(c)
            else:
                c = self._char(*args)
            assets.variables["_speaking_name"] = c.nametag
            assets.variables["_speaking"] = c
            self.char_cache[tuple(args)] = c
        if command == "textbox":
            txt = " ".join(args).replace("{n}","\n")
            tb = textbox(txt)
            tb.can_skip = True
            #tb.skipping = len(txt)
            tb.enter_down()
            tb.update()
    def init(self,*args,**kwargs):
        self.old_stack = assets.stack[:]
        super(DebugScript,self).init(*args,**kwargs)
        self.si2 = 0
        self.kill = 0
        self.o = assets.variables.copy()
        assets.variables["_debug"] = "true"
    def interpret(self):
        if self.si2>=len(self.scriptlines):
            self.kill = 1
            assets.variables.clear()
            assets.variables.update(self.o)
            assets.stack[:] = self.old_stack
            return True
        self.si = self.si2
        line = self.getline()
        self.si2 += 1
        if line:
            self.execute_line(line)
    def run_it(self):
        while not self.kill:
            self.update()
        errors = [o for o in self.obs if isinstance(o,error_msg)]
        return errors
    def debug_game(self,scope="current"):
        scenes = [assets.cur_script.scene]
        if scope == "all":
            scenes = os.listdir(assets.game)
        aerrors = []
        for scene in scenes:
            if scope=="all" and not scene.endswith(".txt"):
                continue
            print scene
            self.world.all = []
            self.init(scene)
            #self.scriptlines = assets.cur_script.scriptlines
            assets.stack.append(self)
            errors = self.run_it()
            print errors
            aerrors.extend(errors)
        if scope == "current":
            for err in reversed(aerrors):
                assets.cur_script.obs.append(err)

def wini():
    f = open("display.ini","w")
    f.write(""";standard width is 256
;standard height is 192
width=%s
height=%s
scale2x=%s
fullscreen=%s
opengl=%s
displaylists=%s
screens=%s
sound_format=%s
sound_bits=%s
sound_buffer=%s
sound_volume=%s
music_volume=%s
screen_compress=%s
autosave=%s"""%(assets.swidth,assets.sheight,assets.filter,assets.fullscreen,
int(pygame.USE_GL),pygame.DISPLAY_LIST,assets.num_screens,
assets.sound_format,assets.sound_bits,assets.sound_buffer,int(assets.sound_volume),int(assets.music_volume),
int(assets.screen_compress),int(assets.autosave)))
    f.close()

class screen_settings(gui.pane):
    firstpane = "resolution"
    def __init__(self,*args,**kwargs):
        gui.widget.__init__(self,*args,**kwargs)
        self.width = 1000
        self.height = 1000
        self.pri = -1001
        self.z = 1001
        self.align = False
        getattr(self,self.firstpane)()
    def make_button(self,text,pos):
        b = gui.button(self,text,pos)
        if screen_settings.firstpane == text:
            b.bgcolor = [50,50,50]
            b.highlightcolor = [50,50,50]
            b.textcolor = [255,255,255]
            print "changed settings for",text
        self.children.append(b)
    def base(self):
        self.children[:] = []
        self.make_button("close",[0,sh-17])
        self.make_button("quit game",[100,sh-17])
        self.make_button("quit pywright",[sw-74,sh-17])
        self.make_button("saves",[50,0])
        self.make_button("resolution",[100,0])
        self.make_button("sound",[170,0])
        if assets.vtrue("_debug"):
            self.make_button("debug",[220,0])
    def debug(self):
        screen_settings.firstpane = "debug"
        self.base()
        line = gui.pane([0,30],[sw,20])
        line.align = "horiz"
        self.children.append(line)
        self.go_script = ""
        line.children.append(gui.editbox(self,"go_script"))
        class myb(gui.button):
            def click_down_over(s,*args):
                assets.cur_script.execute_line(self.go_script)
        line.children.append(myb(None,"execute"))
        cb = line.children[-1]
    def saves(self):
        screen_settings.firstpane = "saves"
        self.base()
        line = gui.pane([0,30],[sw,20])
        line.align = "horiz"
        self.children.append(line)
        line.children.append(gui.label("Autosave on scene changes"))
        class myb(gui.checkbox):
            def click_down_over(self,*args):
                super(myb,self).click_down_over(*args)
                if self.checked:
                    assets.autosave = 1
                else:
                    assets.autosave = 0
                wini()
        line.children.append(myb("autosave"))
        cb = line.children[-1]
        if assets.autosave: cb.checked = True

        line = gui.pane([0,60],[sw,20])
        line.align = "horiz"
        self.children.append(line)
        line.children.append(gui.label("   (All saves make backups)"))
    def sound(self):
        screen_settings.firstpane = "sound"
        self.base()
        ermsg = gui.label("")
        ermsg.rpos = [0,140]
        ermsg.textcol = [255,0,0]
        
        line = gui.pane([0,30],[sw,20])
        line.align = "horiz"
        self.children.append(line)
        class newr(gui.radiobutton):
            def click_down_over(s,*args):
                ermsg.text = ""
                gui.radiobutton.click_down_over(s,*args)
                assets.sound_format = int(s.text)
                if not assets.init_sound(True): 
                    ermsg.text = "Sound not initialized"
                else:
                    assets.play_sound("phoenix/objection.ogg")
                    wini()
        line.children.append(gui.label("Format:"))
        line.children.append(newr("11025","formchoice"))
        line.children.append(newr("22050","formchoice"))
        line.children.append(newr("44100","formchoice"))
        for t in line.children:
            if t.text==str(assets.sound_format):
                t.checked = True
                
        line = gui.pane([0,50],[sw,20])
        line.align = "horiz"
        self.children.append(line)
        class newr(gui.radiobutton):
            def click_down_over(s,*args):
                ermsg.text = ""
                gui.radiobutton.click_down_over(s,*args)
                assets.sound_bits = int(s.text)
                if not assets.init_sound(True): 
                    ermsg.text = "Sound not initialized"
                else:
                    assets.play_sound("phoenix/objection.ogg")
                    wini()
        line.children.append(gui.label("Bits:"))
        line.children.append(newr("8","bitschoice"))
        line.children.append(newr("16","bitschoice"))
        for t in line.children:
            if t.text==str(assets.sound_bits):
                t.checked = True
                
        line = gui.pane([0,70],[sw,20])
        line.align = "horiz"
        self.children.append(line)
        class newr(gui.radiobutton):
            def click_down_over(s,*args):
                ermsg.text = ""
                gui.radiobutton.click_down_over(s,*args)
                assets.sound_buffer = int(s.text)
                if not assets.init_sound(True): 
                    ermsg.text = "Sound not initialized"
                else:
                    assets.play_sound("phoenix/objection.ogg")
                    wini()
        line.children.append(gui.label("Buffer:"))
        line.children.append(newr("512","bufchoice"))
        line.children.append(newr("1024","bufchoice"))
        line.children.append(newr("2048","bufchoice"))
        line.children.append(newr("4096","bufchoice"))
        for t in line.children:
            if t.text==str(assets.sound_buffer):
                t.checked = True
                
        line = gui.pane([0,90],[sw,20])
        line.align = "horiz"
        self.children.append(line)

        self.snd_line = gui.label("SoundVolume: %d"%assets.sound_volume)
        def mod(amt,min,max,var,play):
            def modit():
                ermsg.text = ""
                if not assets.init_sound(): 
                    ermsg.text = "Sound not initialized"
                else:
                    n = getattr(assets,var) + amt
                    if n>max:
                        n = max
                    if n<min:
                        n=min
                    setattr(assets,var,n)
                    self.snd_line.text = "SoundVolume: %d"%assets.sound_volume
                    self.mv_line.text = "MusicVolume: %d"%assets.music_volume
                    play()
                    wini()
            return modit
        line.children.append(self.snd_line)
        line.children.append(gui.button(None,"less"))
        line.children[-1].less = mod(-10,0,100,"sound_volume",lambda:assets.play_sound("phoenix/objection.ogg"))
        line.children.append(gui.button(None,"more"))
        line.children[-1].more = mod(10,0,100,"sound_volume",lambda:assets.play_sound("phoenix/objection.ogg"))
                
        line = gui.pane([0,110],[sw,20])
        line.align = "horiz"
        self.children.append(line)
        
        self.mv_line = gui.label("MusicVolume: %d"%assets.music_volume)
        line.children.append(self.mv_line)
        line.children.append(gui.button(None,"less"))
        line.children[-1].less = mod(-10,0,100,"music_volume",lambda:assets.play_music("Ding.ogg",loop=1,pre="sfx/",reset_track=False))
        line.children.append(gui.button(None,"more"))
        line.children[-1].more = mod(10,0,100,"music_volume",lambda:assets.play_music("Ding.ogg",loop=1,pre="sfx/",reset_track=False))

        self.children.append(ermsg)
    def resolution(self):
        screen_settings.firstpane = "resolution"
        self.base()
        res_box = gui.scrollpane([10,20])
        res_box.width = 200
        res_box.height = 120
        self.res_box = res_box
        self.children.append(res_box)
        
        res_box.children.append(gui.checkbox("fullscreen"))
        self.fs = res_box.children[-1]
        res_box.children.append(gui.checkbox("dualscreen"))
        self.ds = res_box.children[-1]
        res_box.children.append(gui.checkbox("virtual_dualscreen"))
        self.vds = res_box.children[-1]
        res_box.children.append(gui.radiobutton("Change resolution (%sx%s)"%(assets.swidth,assets.sheight),"resopt"))
        res_box.children[-1].checked = True
        res_box.children[-1].click_down_over = self.popup_resolution
        self.reses = gui.radiobutton.groups["resopt"]
        if assets.fullscreen:
            self.fs.checked = True
        if assets.num_screens==2:
            self.ds.checked = True
        if not assets.screen_compress:
            self.vds.checked = True
                
        self.children.append(gui.button(self,"apply",[10,140]))
    def popup_resolution(self,mp):
        self.res_box.children[:] = []
        h = 192
        if get_screen_mode()=="two_screens":
            h*=2
        h2 = h*2
        self.res_box.children.append(gui.radiobutton("DS Res (256x%s)"%h,"resopt"))
        self.res_box.children.append(gui.radiobutton("Double scale (512x%s)"%h2,"resopt"))
        for mode in sorted(pygame.display.list_modes()):
            self.res_box.children.append(gui.radiobutton("(%sx%s)"%mode,"resopt"))
        for r in self.reses:
            if str(assets.swidth)+"x" in r.text and "x"+str(assets.sheight) in r.text:
                r.checked = True
        self.res_box.updatescroll()
    def setdl(self,v):
        self.dislis.checked = 1-self.dislis.checked
        pygame.DISPLAY_LIST = self.dislis.checked
        wini()
    def apply(self):
        for r in self.reses: 
            if r.checked:
                self.oldwidth,self.oldheight = assets.swidth,assets.sheight
                self.timer = 5.0
                self.really_applyb = gui.pane()
                self.really_applyb.is_applyb = True
                self.really_applyb.width = 1000
                self.really_applyb.height = 1000
                self.really_applyb.pri = -1002
                self.really_applyb.z = 1002
                #self.really_applyb.align = False
                e = gui.editbox(None,"")
                e.draw_back = False
                self.really_applyb.children.append(e)
                self.really_applyb.timer = e
                b = gui.button(self,"save_resolution",[0,0])
                self.really_applyb.children.append(b)
                assets.cur_script.obs.append(self.really_applyb)
                assets.swidth,assets.sheight = [int(x) for x in (r.text[r.text.find("(")+1:r.text.find(")")]).split("x")]
        self.old_fullscreen = assets.fullscreen
        assets.fullscreen = 0
        if self.fs.checked:
            assets.fullscreen = 1
        self.old_num_screens = assets.num_screens
        assets.num_screens = 1
        if self.ds.checked:
            assets.num_screens = 2
        assets.screen_compress = 1
        if self.vds.checked:
            assets.screen_compress = 0
        make_screen()
        self.resolution()
    def save_resolution(self):
        for o in assets.cur_script.obs:
            if hasattr(o,"is_applyb"):
                assets.cur_script.world.remove(o)
        self.really_applyb = None
        self.timer = 0
        wini()
        self.resolution()
    def reset_res(self):
        assets.swidth,assets.sheight = self.oldwidth,self.oldheight
        assets.fullscreen = self.old_fullscreen
        assets.num_screens = self.old_num_screens
        make_screen()
    def update(self,*args):
        self.rpos = [0,other_screen(0)]
        self.pos = self.rpos
        if getattr(self,"timer",0)>0:
            self.timer -= .02
            self.really_applyb.timer.text = "Resetting view in: %.02f seconds"%self.timer
        else:
            if getattr(self,"really_applyb",None):
                assets.cur_script.world.remove(self.really_applyb)
                self.really_applyb = None
                self.reset_res()
        return True
    def quit_game(self):
        assets.variables.clear()
        assets.stop_music()
        assets.stack[:] = []
        make_start_script(False)
    def quit_pywright(self):
        sys.exit()
    def close(self):
        self.kill = 1
        
class choose_game(gui.widget):
    def update(self,*args):
        return False
        
def load_game_menu():
    if [1 for o in assets.cur_script.obs if isinstance(o,choose_game)]:
        return
    root = choose_game()
    root.pri = -1000
    root.z = 5000
    root.width,root.height = [sw,sh]
    list = gui.scrollpane([0,0])
    list.width,list.height = [sw,sh]
    root.add_child(list)
    title = gui.editbox(None,"Choose save to load")
    title.draw_back = False
    list.add_child(title)
    list.add_child(gui.button(root,"cancel",pos=[200,0]))
    cb = list.children[-1]
    def cancel(*args):
        print "canceling"
        root.kill = 1
    setattr(root,"cancel",cancel)
    cb.bgcolor = [0, 0, 0]
    cb.textcolor = [255,255,255]
    cb.highlightcolor = [50,75,50]
    assets.cur_script.obs.append(root)
    saves = []
    for p in os.listdir(assets.game+"/"):
        if not p.endswith(".ns"):
            continue
        fp = assets.game+"/"+p
        if os.path.exists(fp):
            saves.append((fp,os.path.getmtime(fp)))
    if os.path.isdir(assets.game+"/save_backup"):
        for f in os.listdir(assets.game+"/save_backup"):
            p = f
            fp = assets.game+"/save_backup/"+p
            saves.append((fp,float(fp.rsplit("_",1)[1])))
    saves.sort(key=lambda a: -a[1])
    i = len(saves)
    for s in saves:
        lt = time.localtime(s[1])
        fn = s[0].rsplit("/",1)[1].split(".",1)[0]
        t = str(i)+") "+fn+" %s/%s/%s %s:%s"%(lt.tm_mon,lt.tm_mday,lt.tm_year,lt.tm_hour,lt.tm_min)
        i -= 1
        item = gui.button(root,t)
        list.add_child(item)
        filename=s[0].replace(assets.game,"")[1:]
        fullpath=s[0]
        def do_load(filename=filename,fullpath=fullpath):
            root.kill = 1
            print "loading",filename,fullpath
            assets.clear()
            assets.load_game_from_string(open(fullpath).read())
        setattr(root,t.replace(" ","_"),do_load)
assets.load_game_menu = load_game_menu
        
def make_start_script(logo=True):
    root = choose_game()
    root.pri = -1000
    root.z = 0
    bottomscript = Script()
    introlines = []
    try:
        import urllib2
        online_script = urllib2.urlopen("http://pywright.dawnsoft.org/updates3/stream/intro_0977.txt",timeout=2)
        introlines = online_script.read().split("\n")
        online_script.close()
    except:
        pass
    bottomscript.init(scriptlines=["fg ../general/logosmall y=-15 name=logo",
                                            "zoom mag=-0.25 frames=30 nowait","add_root"] + introlines + ["gui Wait"])
    assets.stack = [bottomscript]  #So that the root object gets tagged as in bottomscript
    def add_root(command,*args):
        bottomscript.obs.append(root)
    bottomscript._add_root = add_root
    root.width,root.height = [1000,1000]
    root.z = 1000
    
    list = gui.scrollpane([0,other_screen(0)])
    list.width,list.height = [sw,sh]
    root.add_child(list)
    
    title = gui.editbox(None,"Choose a game to run:")
    title.draw_back = False
    list.add_child(title)

    def run_updater(*args):
        import libupdate
        reload(libupdate)
        libupdate.run()
        make_screen()
        make_start_script()
    setattr(make_start_script,"DOWNLOAD_GAMES_AND_CONTENT",run_updater)
    item = gui.button(make_start_script,"DOWNLOAD GAMES AND CONTENT")
    item.bgcolor = [0, 0, 0]
    item.textcolor = [255,255,255]
    item.highlightcolor = [50,75,50]
    list.add_child(item)
    
    for f in os.listdir("games"):
        if f in [".svn"]: continue
        item = gui.button(make_start_script,f)
        d = get_data_from_folder("games/"+f)
        if d.get("icon",""):
            graphic = pygame.image.load("games/"+f+"/"+d["icon"])
        else:
            graphic = pygame.Surface([1,1])
        title = d.get("title",f)
        if d.get("author",""):
            title += " by "+d["author"]
        txt = item.font.render(title,1,[0,0,0])
        req = d.get("min_pywright_version","0")
        reqs = cver_s(req)
        height = graphic.get_height()+txt.get_height()
        width = max(graphic.get_width(),txt.get_width())
        txt2 = None
        if __version__ < req:
            txt2 = item.font.render("Requires PyWright "+reqs,1,[200,20,30])
            height += txt2.get_height()
            width = max(graphic.get_width(),txt.get_width(),txt2.get_width())
        image = pygame.Surface([width,height])
        image.fill([200,200,255])
        image.blit(graphic,[0,0])
        image.blit(txt,[0,graphic.get_height()])
        if txt2:
            image.blit(txt2,[0,graphic.get_height()+txt.get_height()])
        item.graphic = image
        list.add_child(item)
        def _play_game(func=f):
            gamedir = os.path.join("games",func)
            assets.game = gamedir
            scr = Script()
            scr.init()
            scr.obs = []
            assets.stack = [scr]
            scr.obs.append(bg("main"))
            scr.obs.append(bg("main",screen=2))
            case_select = case_menu(gamedir)
            case_select.reload = True
            scr.obs.append(case_select)
        if __version__ >= req:
            setattr(make_start_script,f.replace(" ","_"),_play_game)
        else:
            setattr(make_start_script,f.replace(" ","_"),lambda: 1)
            

def make_screen():
    if not hasattr(assets,"cur_screen"):
        assets.cur_screen = 0
    try:
        SCREEN=pygame.real_screen = pygame.display.set_mode([assets.swidth,assets.sheight],pygame.RESIZABLE|pygame.HWSURFACE|pygame.DOUBLEBUF|pygame.FULLSCREEN*assets.fullscreen)
    except:
        SCREEN=pygame.real_screen = pygame.display.set_mode([assets.swidth,assets.sheight],pygame.RESIZABLE|pygame.FULLSCREEN*assets.fullscreen|pygame.DOUBLEBUF)
    ns = assets.num_screens
    if assets.cur_screen:
        ns = 2
    pygame.screen = pygame.Surface([sw,sh*2]).convert()
    pygame.blank = pygame.screen.convert()
    pygame.blank.fill([0,0,0])
    pygame.display.set_caption("PyWright "+VERSION)
    pygame.display.set_icon(pygame.image.load("art/general/bb.png"))
    if pygame.joystick.get_init():
        pygame.joystick.quit()
    pygame.joystick.init()
    pygame.js1 = None
    if pygame.joystick.get_count():
        pygame.js1 = pygame.joystick.Joystick(0)
        pygame.js1.init()
    def gl():
        return pygame.js1 and pygame.js1.get_numhats() and pygame.js1.get_hat(0)[0]<0
    def gr():
        return pygame.js1 and pygame.js1.get_numhats() and pygame.js1.get_hat(0)[0]>0
    def gu():
        return pygame.js1 and pygame.js1.get_numhats() and pygame.js1.get_hat(0)[1]>0
    def gd():
        return pygame.js1 and pygame.js1.get_numhats() and pygame.js1.get_hat(0)[1]<0
    pygame.jsleft = gl
    pygame.jsright = gr
    pygame.jsup = gu
    pygame.jsdown = gd

def fit(surf,size):
    if surf.get_width()<size[0]:
        surf = pygame.transform.scale2x(surf)
    surf = pygame.transform.scale(surf,size)
    return surf
def get_screen_mode():
    mode="two_screens"
    if assets.num_screens == 1:
        mode = "squished"
        if assets.screen_compress:
            mode = "show_one"
    return mode
def get_screen_dim(mode,aspect=True):
    raspect = assets.swidth/float(assets.sheight)
    if mode == "two_screens":
        aspect = 256.0/(192.0*2)
        top_pos = [0,0]
        top_size = [1,0.5]
        bottom_pos = [0,0.5]
        bottom_size = [1,0.5]
        if aspect:
            top_size[0]*=aspect/raspect
            bottom_size[0]*=aspect/raspect
            top_pos[0]=(1-top_size[0])/2.0
            bottom_pos[0]=(1-bottom_size[0])/2.0
    if mode == "horizontal":
        top_pos = [0,0]
        top_size = [0.5,0.75]
        bottom_pos = [0.5,0.25]
        bottom_size = [0.5,0.75]
    if mode == "squished":
        top_pos = [0,0]
        top_size = [1,1]
        bottom_pos = None
    if mode == "show_one":
        if assets.cur_screen == 0:
            top_pos = [0,0]
            top_size = [1,1]
            bottom_pos = None
        else:
            top_pos = None
            bottom_pos = [0,0]
            bottom_size = [1,1]
    d = {"top":None,"bottom":None}
    if top_pos:
        top_pos_t = [top_pos[0]*assets.swidth,top_pos[1]*assets.sheight]
        top_size_t = [top_size[0]*assets.swidth,top_size[1]*assets.sheight]
        d["top"] = [top_pos,top_size,top_pos_t,top_size_t]
    if bottom_pos:
        bottom_pos_t = [bottom_pos[0]*assets.swidth,bottom_pos[1]*assets.sheight]
        bottom_size_t = [bottom_size[0]*assets.swidth,bottom_size[1]*assets.sheight]
        d["bottom"] = [bottom_pos,bottom_size,bottom_pos_t,bottom_size_t]
    return d
def translate_click(pos):
    mode = get_screen_mode()
    dim = get_screen_dim(mode)
    def col(pp,ss):
        if pos[0]>=pp[0] and pos[0]<=pp[0]+ss[0]\
            and pos[1]>=pp[1] and pos[1]<=pp[1]+ss[1]:
            x = pos[0]-pp[0]
            x = x/float(ss[0])*sw
            y = pos[1]-pp[1]
            y = y/float(ss[1])*sh
            return [int(x),int(y)]
    if dim["top"]:
        r = col(*dim["top"][2:])
        if r:
            return r
    if dim["bottom"]:
        r = col(*dim["bottom"][2:])
        if r:
            r[1]+=sh
            return r
    return [-100000,-100000]
def draw_screen():
    scale = 0
    if assets.sheight!=sh or assets.swidth!=sw: scale = 1
    scaled = pygame.screen
    top = scaled.subsurface([[0,0],[sw,sh]])
    bottom = top
    mode = get_screen_mode()
    dim = get_screen_dim(mode)
    if mode == "two_screens" or mode == "horizontal" or mode == "show_one":
        bottom = scaled.subsurface([[0,sh],[sw,sh]])
    if assets.swidth>256 and scale:
        scaled = pygame.transform.scale2x(pygame.screen)
    if scale:
        scaled = pygame.transform.scale(scaled,[assets.swidth,assets.sheight])
    pygame.real_screen.fill([10,10,10])
    def draw_segment(dest,surf,pos,size):
        rp = [pos[0]*assets.swidth,pos[1]*assets.sheight]
        rs = [size[0]*assets.swidth,size[1]*assets.sheight]
        surf = fit(surf,rs)
        dest.blit(surf,rp)
    if dim["top"]:
        draw_segment(pygame.real_screen,top,dim["top"][0],dim["top"][1])
    if dim["bottom"]:
        draw_segment(pygame.real_screen,bottom,dim["bottom"][0],dim["bottom"][1])
    pygame.display.flip()
assets.make_screen = make_screen
assets.draw_screen = draw_screen

def run(checkupdate=False):
    import sys,os
    

    #Check for updates!
    newengine = None
    if checkupdate:
        import libupdate
        eng = libupdate.Engine()
        libupdate.screen.blit(arial14.render("Checking for Updates...",1,[255,255,255]),[0,0])
        pygame.display.flip()
        libupdate.root.start_index = 0
        try:
            assets.threads = [eng.Update_PyWright(thread=True)]
            pygame.event.clear()
            pygame.event.pump()
            while libupdate.list.status_box.text=="Fetching data from server...":
                libupdate.screen.fill([0,0,0])
                libupdate.screen.blit(arial14.render("Checking for Updates... (Click to cancel)",1,[255,255,255]),[0,0])
                pygame.display.flip()
                for e in pygame.event.get():
                    if e.type == pygame.MOUSEBUTTONDOWN:
                        libupdate.list.status_box.text = "cancelled"
            libupdate.screen.fill([0,0,0])
            if libupdate.list.status_box.text == "cancelled":
                libupdate.screen.blit(arial14.render("Cancelled checking for updates",1,[255,255,255]),[0,0])
            else:
                libupdate.screen.blit(arial14.render("Finished checking for updates",1,[255,255,255]),[0,0])
            pygame.display.flip()
            for pane in libupdate.list.children[2:]:
                c = pane.children[1].children[0]
                if isinstance(c,gui.checkbox):
                    c.checked = True
                    libupdate.Engine.quit_threads = 0
                    libupdate.screen.blit(arial14.render("Doing update to "+c.text,1,[255,255,255]),[0,20])
                    pygame.display.flip()
                    eng.do_update(output=True)
                    goodkeys = "copy_reg,sre_compile,locale,_sre,__main__,site,__builtin__,\
operator,encodings,os.path,encodings.encodings,encodings.cp437,errno,\
encodings.codecs,sre_constants,re,ntpath,UserDict,nt,stat,zipimport,warnings,\
encodings.types,_codecs,encodings.cp1252,sys,codecs,types,_types,_locale,signal,\
linecache,encodings.aliases,exceptions,sre_parse,os,goodkeys,k,core,libengine".split(",")
                    for k in sys.modules.keys():
                        if k not in goodkeys:
                            del sys.modules[k]
                    import core as core2
                    reload(core2)
                    import libengine as le2
                    reload(le2)
                    newengine = le2.run
                    break
        except SystemExit:
            sys.exit()
        #~ except:
            #~ pass
    if newengine:
        newengine()
        sys.exit()
    
    assets.init_sound()
    assets.fullscreen = 0
    assets.swidth = 256
    assets.sheight = 192*2
    assets.filter = 0
    assets.num_screens = 2
    assets.screen_compress = 0  #Whether to move objects on screen 2 to screen 1 if num_screens is 1
    assets.autosave = 1
    pygame.USE_GL=1
    pygame.DISPLAY_LIST=1
    pygame.TEXTURE_CACHE=0
    if os.path.exists("display.ini"):
        f = open("display.ini","r")
        for line in f.readlines():
            spl = line.split("=")
            if len(spl)!=2: continue
            if spl[0]=='width': assets.swidth = int(float(spl[1]))
            if spl[0]=='height': assets.sheight = int(float(spl[1]))
            if spl[0]=='scale2x': assets.filter = int(spl[1])
            if spl[0]=='fullscreen': assets.fullscreen = int(spl[1])
            if spl[0]=="opengl": pygame.USE_GL = int(spl[1])
            if spl[0]=="screens": assets.num_screens = int(spl[1])
            if spl[0]=="displaylists": pygame.DISPLAY_LIST = int(spl[1])
            if spl[0]=="sound_format": assets.sound_format = int(spl[1])
            if spl[0]=="sound_bits": assets.sound_bits = int(spl[1])
            if spl[0]=="sound_buffer": assets.sound_buffer = int(spl[1])
            if spl[0]=="sound_volume": assets.sound_volume = float(spl[1])
            if spl[0]=="music_volume": assets.music_volume = float(spl[1])
            if spl[0]=="screen_compress": assets.screen_compress = int(spl[1])
            if spl[0]=="autosave": assets.autosave = int(spl[1])
    wini()
    
    pygame.USE_GL=0
    make_screen()

    #assets.master_volume = 0.0
        

    game = "menu"
    scene = "intro"
    if sys.argv[1:] and sys.argv[2:]:
        game = sys.argv[1]
        scene = sys.argv[2]
    assets.game = game
    assets.items = []

    running = True

    showfps = False
    clock = pygame.time.Clock()

    make_start_script()
    import time
    lt = time.time()
    ticks = 0
    fr = 0
    #~ import time
    #~ end = time.time()+5
    #~ while time.time()<end:
        #~ pass
    #~ sys.exit()

    while running:
        #~ ticks = time.time()-lt
        #~ lt = time.time()
        #~ while ticks<(1/(float(assets.variables.get("_framerate",60))+20.0)):
            #~ if ticks: time.sleep(0.02)
            #~ ticks += time.time()-lt
            #~ lt = time.time()
        #~ dt = ticks*1000.0
        dt = clock.tick(60)
        assets.cur_script.update()
        if not assets.cur_script: break
        [o.unadd() for o in assets.cur_script.obs if getattr(o,"kill",0) and hasattr(o,"unadd")]
        for o in assets.cur_script.world.all[:]:
            if getattr(o,"kill",0):
                assets.cur_script.world.all.remove(o)
        pygame.screen.blit(pygame.blank,[0,0])
        try:
            assets.cur_script.draw(pygame.screen)
        except (art_error,script_error),e:
            assets.cur_script.obs.append(error_msg(e.value,assets.cur_script.lastline_value,assets.cur_script.si,assets.cur_script))
        if assets.flash:
            fl = flash()
            assets.cur_script.obs.append(fl)
            fl.ttl = assets.flash
            if hasattr(assets,"flashcolor"):
                fl.color = assets.flashcolor
                assets.flashcolor = [255,255,255]
            assets.flash = 0
        if assets.shakeargs:
            assets.cur_script._shake(*assets.shakeargs)
            assets.shakeargs = 0
        if showfps:
            pygame.screen.blit(font.render(str(1/(dt/1000.0)),[100,180,200]),[0,0])
            #~ y = 12
            #~ for s in assets.stack:
                #~ for i in range(len(s.obs)):
                    #~ pygame.screen.blit(arial10.render(str(s.obs[i]),1,[100,180,200]),[0,y])
                    #~ y+=10
                #~ y+=2
        if assets.variables.get("render",1):
            draw_screen()
        #pygame.image.save(pygame.real_screen,"capture/img%.04d.jpg"%fr)
        #fr+=1
        pygame.event.pump()
        try:
            assets.cur_script.handle_events(pygame.event.get([pygame.MOUSEMOTION,pygame.MOUSEBUTTONUP,pygame.MOUSEBUTTONDOWN]))
            if "enter" in assets.cur_script.held:
                for o in assets.cur_script.upobs:
                    if hasattr(o,"enter_hold"):
                        o.enter_hold()
            for e in pygame.event.get():
                if e.type==150:
                    if assets.variables.get("_music_loop",None):
                        assets.play_music(assets.variables["_music_loop"])
                if e.type==pygame.ACTIVEEVENT:
                    if e.gain==0 and (e.state==6 or e.state==2):
                        print "minimize"
                        assets.mini_vol = (assets.sound_volume,assets.music_volume)
                        assets.sound_volume = 0
                        assets.music_volume = 0
                        gw = guiWait()
                        gw.minimized = True
                        assets.cur_script.obs.append(gw)
                    if e.gain==1 and e.state==6:
                        print "maximize"
                        if hasattr(assets,"mini_vol"):
                            (assets.sound_volume,assets.music_volume) = assets.mini_vol
                            del assets.mini_vol
                        for ob in assets.cur_script.obs:
                            if hasattr(ob,"minimized"):
                                assets.cur_script.world.all.remove(ob)
                if e.type==pygame.VIDEORESIZE:
                    w,h = e.w,e.h
                    #w = (256/192.0)*h
                    assets.swidth = w
                    assets.sheight = h
                    make_screen()
                    wini()
                if e.type==pygame.KEYDOWN and \
                e.key==pygame.K_ESCAPE:
                    ss = [x for x in assets.cur_script.obs if isinstance(x,screen_settings)]
                    if ss:
                        ss[0].kill = 1
                    else:
                        assets.cur_script.obs.append(screen_settings())
                        #print [o.z for o in assets.cur_script.obs]
                if e.type == pygame.QUIT:
                    running = False
                if e.type == pygame.KEYDOWN and e.key == pygame.K_c:
                    print "scripts",assets.stack
                    print "objects",[len(x.obs) for x in assets.stack]
                    print assets.cur_script.obs
                    print [getattr(o,"kill",0) for o in assets.cur_script.obs]
                if (e.type==pygame.KEYUP and\
                e.key==pygame.K_RETURN) or (e.type==pygame.JOYBUTTONUP and\
                e.button==1):
                    if "enter" in assets.cur_script.held: assets.cur_script.held.remove("enter")
                    for o in assets.cur_script.upobs:
                        if hasattr(o,"enter_up"):
                            o.enter_up()
                            break
                if e.type==pygame.KEYDOWN and\
                e.key==pygame.K_RETURN and pygame.key.get_mods() & pygame.KMOD_ALT:
                    assets.fullscreen = 1-assets.fullscreen
                    make_screen()
                    wini()
                elif (e.type==pygame.KEYDOWN and\
                e.key==pygame.K_RETURN) or (e.type==pygame.JOYBUTTONDOWN and\
                e.button==0):
                    if "enter" not in assets.cur_script.held: assets.cur_script.held.append("enter")
                    for o in assets.cur_script.upobs:
                        if hasattr(o,"enter_down") and not getattr(o,"kill",0) and not getattr(o,"hidden",0):
                            o.enter_down()
                            if isinstance(o,evidence_menu):
                                if "enter" in assets.cur_script.held:
                                    assets.cur_script.held.remove("enter")
                            if isinstance(o,examine_menu):
                                if "enter" in assets.cur_script.held:
                                    assets.cur_script.held.remove("enter")
                            break
                if (e.type==pygame.KEYDOWN and\
                e.key==pygame.K_RIGHT) or (e.type==pygame.JOYHATMOTION and e.value[0]==1):
                    for o in assets.cur_script.upobs:
                        if hasattr(o,"statement") and not o.statement:
                            continue
                        if hasattr(o,"k_right") and not getattr(o,"kill",0) and not getattr(o,"hidden",0):
                            o.k_right()
                            break
                if (e.type==pygame.KEYDOWN and\
                e.key==pygame.K_LEFT) or (e.type==pygame.JOYHATMOTION and e.value[0]==-1):
                    for o in assets.cur_script.upobs:
                        if hasattr(o,"statement") and not o.statement:
                            continue
                        if hasattr(o,"k_left") and not getattr(o,"kill",0) and not getattr(o,"hidden",0):
                            o.k_left()
                            break
                if (e.type==pygame.KEYDOWN and\
                e.key==pygame.K_UP) or (e.type==pygame.JOYHATMOTION and e.value[1]==1):
                    for o in assets.cur_script.upobs:
                        if hasattr(o,"k_up") and not getattr(o,"kill",0) and not getattr(o,"hidden",0):
                            o.k_up()
                            break
                if (e.type==pygame.KEYDOWN and\
                e.key==pygame.K_DOWN) or (e.type==pygame.JOYHATMOTION and e.value[1]==-1):
                    for o in assets.cur_script.upobs:
                        if hasattr(o,"k_down") and not getattr(o,"kill",0) and not getattr(o,"hidden",0):
                            o.k_down()
                            break
                if (e.type==pygame.KEYDOWN and\
                e.key==pygame.K_SPACE) or (e.type==pygame.JOYBUTTONDOWN and\
                e.button==1):
                    for o in assets.cur_script.upobs:
                        if hasattr(o,"k_space") and not getattr(o,"kill",0) and not getattr(o,"hidden",0):
                            o.k_space()
                            break
                if (e.type==pygame.KEYDOWN and \
                    e.key == pygame.K_TAB) or (e.type==pygame.JOYBUTTONDOWN and\
                e.button==3):
                    for o in assets.cur_script.upobs:
                        if hasattr(o,"k_tab") and not getattr(o,"kill",0) and not getattr(o,"hidden",0):
                            o.k_tab()
                            break
                if (e.type==pygame.KEYDOWN and\
                e.key==pygame.K_z) or (e.type==pygame.JOYBUTTONDOWN and\
                e.button==4):
                    for o in assets.cur_script.upobs:
                        if hasattr(o,"k_z") and not getattr(o,"kill",0) and not getattr(o,"hidden",0):
                            o.k_z()
                            break
                if (e.type==pygame.KEYDOWN and\
                e.key==pygame.K_x) or (e.type==pygame.JOYBUTTONDOWN and\
                e.button==5):
                    for o in assets.cur_script.upobs:
                        if hasattr(o,"k_x") and not getattr(o,"kill",0) and not getattr(o,"hidden",0):
                            o.k_x()
                            break
                if (e.type==pygame.KEYDOWN and \
                    e.key==pygame.K_LSHIFT) or (e.type==pygame.JOYBUTTONDOWN and\
                    e.button==6):
                    assets.cur_screen = 1-assets.cur_screen
                    make_screen()
                if e.type==pygame.KEYDOWN and e.key==pygame.K_d and e.mod&pygame.K_LCTRL:
                    assets.variables["_debug"] = "true"
                if e.type==pygame.KEYDOWN and\
                e.key==pygame.K_F5 and assets.game!="menu":
                    assets.save_game()
                if e.type==pygame.KEYDOWN and\
                e.key == pygame.K_F7 and assets.game!="menu":
                    load_game_menu()
                    #assets.load_game(assets.game)
                if e.type==pygame.KEYDOWN and\
                e.key == pygame.K_F9:
                    print "debugging game"
                    s = DebugScript()
                    s.debug_game()
                    print "finished"
                assets.cur_script.handle_events([e])
            #~ if pygame.js1:
                #~ print pygame.js1.get_button(0)
        except script_error, e:
            assets.cur_script.obs.append(error_msg(e.value,assets.cur_script.lastline_value,assets.cur_script.si,assets.cur_script))
            import traceback
            traceback.print_exc()
    if hasattr(assets, "threads"):
        while [1 for thread in assets.threads if thread and thread.isAlive()]:
            print "waiting"
            pass
if __name__=="__main__":
    run()
