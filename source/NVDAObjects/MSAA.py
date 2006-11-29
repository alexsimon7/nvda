import time
import struct
import difflib
import ctypes
import comtypes.automation
import comtypesClient
import debug
import MSAAHandler
import winUser
import winKernel
import audio
import api
from config import conf
from constants import *
import window
import textBuffer
import manager
import ITextDocument

class NVDAObject_MSAA(window.NVDAObject_window):

	def __init__(self,*args):
		self.ia=args[0]
		self.child=args[1]
		window.NVDAObject_window.__init__(self,MSAAHandler.windowFromAccessibleObject(self.ia))
		self.allowedPositiveStates=STATE_SYSTEM_UNAVAILABLE|STATE_SYSTEM_SELECTED|STATE_SYSTEM_PRESSED|STATE_SYSTEM_CHECKED|STATE_SYSTEM_MIXED|STATE_SYSTEM_READONLY|STATE_SYSTEM_EXPANDED|STATE_SYSTEM_COLLAPSED|STATE_SYSTEM_BUSY|STATE_SYSTEM_HASPOPUP
		self._lastPositiveStates=self.calculatePositiveStates()
		self._lastNegativeStates=self.calculateNegativeStates()

	def __hash__(self):
		l=10000000
		p=17
		h=window.NVDAObject_window.__hash__(self)
		role=self.role
		if isinstance(role,basestring):
			role=hash(role)
		if isinstance(role,int):
			h=(h+(role*p))%l
		childID=self.childID
		if isinstance(childID,int):
			h=(h+(childID*p))%l
		location=self.location
		if location and (len(location)==4):
			left,top,width,height=location
			h=(h+(left*p))%l
			h=(h+(top*p))%l
			h=(h+(width*p))%l
			h=(h+(height*p))%l
		return h

	def _get_name(self):
		return MSAAHandler.accName(self.ia,self.child)

	def _get_value(self):
		return MSAAHandler.accValue(self.ia,self.child)

	def _get_role(self):
		return MSAAHandler.accRole(self.ia,self.child)

	def _get_typeString(self):
		role=self.role
		if conf["presentation"]["reportClassOfAllObjects"] or (conf["presentation"]["reportClassOfClientObjects"] and (role==ROLE_SYSTEM_CLIENT)):
			typeString=self.className
		else:
			typeString=""
		return typeString+" %s"%MSAAHandler.getRoleName(self.role)

	def _get_states(self):
		return MSAAHandler.accState(self.ia,self.child)

	def getStateName(self,state,opposite=False):
		if isinstance(state,int):
			newState=MSAAHandler.getStateText(state)
		else:
			newState=state
		if opposite:
			newState=_("not")+" "+newState
		return newState

	def _get_description(self):
		try:
			return self.ia.accDescription(self.child)
		except:
			return ""

	def _get_keyboardShortcut(self):
		keyboardShortcut=None
		try:
			keyboardShortcut=self.ia.accKeyboardShortcut(self.child)
		except:
			return ""
		if not keyboardShortcut:
			return ""
		else:
			return keyboardShortcut

	def _get_childID(self):
		try:
			return self.child
		except:
			return None

	def _get_childCount(self):
		count=MSAAHandler.accChildCount(self.ia,self.child)
		return count

	def _get_location(self):
		location=MSAAHandler.accLocation(self.ia,self.child)
		return location

	def _get_parent(self):
		res=MSAAHandler.accParent(self.ia,self.child)
		if res:
			(ia,child)=res
		else:
			return None
		obj=manager.getNVDAObjectByAccessibleObject(ia,child)
		if obj and (obj.role==ROLE_SYSTEM_WINDOW):
			return obj.parent
		else:
			return obj

	def _get_next(self):
		res=MSAAHandler.accParent(self.ia,self.child)
		if res:
			parentObject=manager.getNVDAObjectByAccessibleObject(res[0],res[1])
			parentRole=parentObject.role
		else:
			parentObject=None
			parentRole=None
		if parentObject and (parentRole==ROLE_SYSTEM_WINDOW):
			obj=parentObject
		else:
			obj=self
		res=MSAAHandler.accNavigate(obj.ia,obj.child,NAVDIR_NEXT)
		if res:
			nextObject=manager.getNVDAObjectByAccessibleObject(res[0],res[1])
			if nextObject and (nextObject.role==ROLE_SYSTEM_WINDOW):
				nextObject=manager.getNVDAObjectByLocator(nextObject.hwnd,-4,0)
			if nextObject!=self:
				return nextObject
			else:
				return None

	def _get_previous(self):
		res=MSAAHandler.accParent(self.ia,self.child)
		if res:
			parentObject=manager.getNVDAObjectByAccessibleObject(res[0],res[1])
			parentRole=parentObject.role
		else:
			parentObject=None
			parentRole=None
		if parentObject and (parentRole==ROLE_SYSTEM_WINDOW):
			obj=parentObject
		else:
			obj=self
		res=MSAAHandler.accNavigate(obj.ia,obj.child,NAVDIR_PREVIOUS)
		if res:
			previousObject=manager.getNVDAObjectByAccessibleObject(res[0],res[1])
			if previousObject and (previousObject.role==ROLE_SYSTEM_WINDOW):
				previousObject=manager.getNVDAObjectByLocator(previousObject.hwnd,-4,0)
			if previousObject!=self:
				return previousObject
			else:
				return None

	def _get_firstChild(self):
		res=MSAAHandler.accNavigate(self.ia,self.child,NAVDIR_FIRSTCHILD)
		if res:
			obj=manager.getNVDAObjectByAccessibleObject(res[0],res[1])
		else:
			return None
		if obj and (obj.role==ROLE_SYSTEM_WINDOW):
			return manager.getNVDAObjectByLocator(obj.hwnd,OBJID_CLIENT,0)
		else:
			return obj

	def doDefaultAction(self):
		MSAAHandler.accDoDefaultAction(self.ia,self.child)

	def _get_activeChild(self):
		res=MSAAHandler.accFocus()
		if res:
			return manager.getNVDAObjectByAccessibleObject(res[0],res[1])

	def hasFocus(self):
		states=0
		states=self.states
		if (states&STATE_SYSTEM_FOCUSED):
			return True
		else:
			return False

	def setFocus(self):
		self.ia.SetFocus()

	def _get_positionString(self):
		position=""
		childID=self.childID
		if childID>0:
			parent=self.parent
			if parent:
				parentChildCount=parent.childCount
				if parentChildCount>=childID:
					position="%s of %s"%(childID,parentChildCount)
		return position

	def event_foreground(self):
		audio.cancel()
		self.speakObject()

	def event_show(self):
		if self.role==ROLE_SYSTEM_MENUPOPUP:
			self.event_menuStart()

	def updateMenuMode(self):
		if self.role not in [ROLE_SYSTEM_MENUBAR,ROLE_SYSTEM_MENUPOPUP,ROLE_SYSTEM_MENUITEM]:
			api.setMenuMode(False)
		if self.role==ROLE_SYSTEM_MENUITEM:
			audio.cancel()

	def event_mouseMove(self,x,y,oldX,oldY):
		location=self.location
		if not location or (len(location)!=4):
			return
		(left,top,width,height)=location
		right=left+width
		bottom=top+height
		if (oldX<left) or (oldX>right) or (oldY<top) or (oldY>bottom):
			audio.cancel()
			self.speakObject()

	def event_gainFocus(self):
		self.updateMenuMode()
		if self.hasFocus() and not (not api.getMenuMode() and (self.role==ROLE_SYSTEM_MENUITEM)) and not ((self.hwnd==winUser.getForegroundWindow()) and (self.role==ROLE_SYSTEM_CLIENT)):
			self.speakObject()

	def event_menuStart(self):
		if self.role not in [ROLE_SYSTEM_MENUBAR,ROLE_SYSTEM_MENUPOPUP,ROLE_SYSTEM_MENUITEM]:
			return
		if not api.getMenuMode():
			audio.cancel()
			api.setMenuMode(True)
			self.speakObject()
			for child in self.children:
				if child.hasFocus():
					child.speakObject()
					break

	def event_valueChange(self):
		if self.hasFocus():
			audio.speakObjectProperties(value=self.value)

	def event_nameChange(self):
		if self.hasFocus():
			audio.speakObjectProperties(name=self.name)

	def event_stateChange(self):
		positiveStates=self.calculatePositiveStates()
		newPositiveStates=positiveStates-(positiveStates&self._lastPositiveStates)
		negativeStates=self.calculateNegativeStates()
		newNegativeStates=negativeStates-(negativeStates&self._lastNegativeStates)
		if self.hasFocus():
			if newPositiveStates:
				audio.speakObjectProperties(stateText=self.getStateNames(newPositiveStates))
			if newNegativeStates:
				audio.speakObjectProperties(stateText=self.getStateNames(newNegativeStates,opposite=True))
		self._lastPositiveStates=positiveStates
		self._lastNegativeStates=negativeStates

	def event_selection(self):
		return self.event_stateChange()

	def event_selectionAdd(self):
		return self.event_stateChange()

	def event_selectionRemove(self):
		return self.event_stateChange()

	def event_selectionWithIn(self):
		return self.event_stateChange()

class NVDAObject_dialog(NVDAObject_MSAA):
	"""
	Based on NVDAObject but on foreground events, the dialog contents gets read.
	"""

	def event_foreground(self):
		self.speakObject()
		for child in self.children:
			states=child.states
			if (not states&STATE_SYSTEM_OFFSCREEN) and (not states&STATE_SYSTEM_INVISIBLE) and (not states&STATE_SYSTEM_UNAVAILABLE):
				child.speakObject()
				if child.states&STATE_SYSTEM_FOCUSED:
					audio.speakObjectProperties(stateText=child.getStateName(STATE_SYSTEM_FOCUSED))
				if child.states&STATE_SYSTEM_DEFAULT:
					audio.speakObjectProperties(stateText=child.getStateName(STATE_SYSTEM_DEFAULT))
			if child.role==ROLE_SYSTEM_PROPERTYPAGE:
				for grandChild in child.children:
					states=grandChild.states
					if (not states&STATE_SYSTEM_OFFSCREEN) and (not states&STATE_SYSTEM_INVISIBLE) and (not states&STATE_SYSTEM_UNAVAILABLE):
						grandChild.speakObject()
						if grandChild.states&STATE_SYSTEM_FOCUSED:
							audio.speakObjectProperties(stateText=grandChild.getStateName(STATE_SYSTEM_FOCUSED))
						if grandChild.states&STATE_SYSTEM_DEFAULT:
							audio.speakObjectProperties(stateText=grandChild.getStateName(STATE_SYSTEM_DEFAULT))

class NVDAObject_TrayClockWClass(NVDAObject_MSAA):
	"""
	Based on NVDAObject but the role is changed to clock.
	"""

	def _get_role(self):
		return ROLE_SYSTEM_CLOCK

class NVDAObject_Shell_TrayWnd(NVDAObject_MSAA):
	"""
	Based on NVDAObject but on foreground events nothing gets spoken.
	This is the window which holds the windows start button and taskbar.
	"""
 
	def event_foreground(self):
		pass

	def event_gainFocus(self):
		pass

class NVDAObject_Progman(NVDAObject_MSAA):
	"""
	Based on NVDAObject but on foreground events nothing gets spoken.
	This is the window which holds the windows desktop.
	"""

	def event_foreground(self):
		pass

	def event_gainFocus(self):
		pass

class NVDAObject_staticText(textBuffer.NVDAObject_textBuffer,NVDAObject_MSAA):

	def __init__(self,*args):
		NVDAObject_MSAA.__init__(self,*args)
		textBuffer.NVDAObject_textBuffer.__init__(self,*args)

class NVDAObject_edit(textBuffer.NVDAObject_editableTextBuffer,NVDAObject_MSAA):

	def __init__(self,*args):
		NVDAObject_MSAA.__init__(self,*args)
		textBuffer.NVDAObject_editableTextBuffer.__init__(self,*args)

	def _get_value(self):
		return self.currentLine

	def _get_caretRange(self):
		long=winUser.sendMessage(self.hwnd,EM_GETSEL,0,0)
		start=winUser.LOWORD(long)
		end=winUser.HIWORD(long)
		return (start,end)

	def _get_caretPosition(self):
		long=winUser.sendMessage(self.hwnd,EM_GETSEL,0,0)
		pos=winUser.LOWORD(long)
		return pos

	def _set_caretPosition(self,pos):
		winUser.sendMessage(self.hwnd,EM_SETSEL,pos,pos)

	def _get_lineCount(self):
		lineCount=winUser.sendMessage(self.hwnd,EM_GETLINECOUNT,0,0)
		if lineCount<0:
			return None
		return lineCount

	def getLineNumber(self,pos):
		return winUser.sendMessage(self.hwnd,EM_LINEFROMCHAR,pos,0)

	def getPositionFromLineNumber(self,lineNum):
		return winUser.sendMessage(self.hwnd,EM_LINEINDEX,lineNum,0)

	def getLineStart(self,pos):
		lineNum=self.getLineNumber(pos)
		return winUser.sendMessage(self.hwnd,EM_LINEINDEX,lineNum,0)

	def getLineLength(self,pos):
		lineLength=winUser.sendMessage(self.hwnd,EM_LINELENGTH,pos,0)
		if lineLength<0:
			return None
		return lineLength

	def getLine(self,pos):
		lineNum=self.getLineNumber(pos)
		lineLength=self.getLineLength(pos)
		if not lineLength:
			return None
		sizeData=struct.pack('h',lineLength)
		buf=ctypes.create_unicode_buffer(sizeData,size=lineLength)
		res=winUser.sendMessage(self.hwnd,EM_GETLINE,lineNum,buf)
		return buf.value

	def nextLine(self,pos):
		lineNum=self.getLineNumber(pos)
		if lineNum+1<self.lineCount:
			return self.getPositionFromLineNumber(lineNum+1)

	def previousLine(self,pos):
		lineNum=self.getLineNumber(pos)
		if lineNum-1>=0:
			return self.getPositionFromLineNumber(lineNum-1)

	def event_caret(self):
		self._reviewCursor=self.caretPosition

	def event_valueChange(self):
		pass


class NVDAObject_checkBox(NVDAObject_MSAA):
	"""
	Based on NVDAObject, but filterStates removes the pressed state for checkboxes.
	"""

	def __init__(self,*args):
		NVDAObject_MSAA.__init__(self,*args)
		self.allowedPositiveStates=self.allowedPositiveStates-(self.allowedPositiveStates&STATE_SYSTEM_PRESSED)
		self.allowedNegativeStates=self.allowedNegativeStates|STATE_SYSTEM_CHECKED
		self._lastPositiveStates=self.calculatePositiveStates()
		self._lastNegativeStates=self.calculateNegativeStates()

class NVDAObject_outlineItem(NVDAObject_MSAA):

	def _get_value(self):
		return "level %s"%super(NVDAObject_outlineItem,self).value


class NVDAObject_tooltip(NVDAObject_MSAA):

	def _get_name(self):
		name=super(NVDAObject_tooltip,self).name
		value=super(NVDAObject_tooltip,self).value
		if name and not value:
			return ""
		else:
			return name

	def _get_value(self):
		name=super(NVDAObject_tooltip,self).name
		value=super(NVDAObject_tooltip,self).value
		if name and not value:
			return name
		else:
			return ""

	def event_toolTip(self):
		if conf["presentation"]["reportTooltips"]:
			self.speakObject()

class NVDAObject_consoleWindowClass(NVDAObject_MSAA):

	def event_nameChange(self):
		pass

class NVDAObject_consoleWindowClassClient(textBuffer.NVDAObject_editableTextBuffer,NVDAObject_MSAA):

	def __init__(self,*args):
		NVDAObject_MSAA.__init__(self,*args)
		processID=self.processID[0]
		try:
			winKernel.freeConsole()
		except:
			debug.writeException("freeConsole")
			pass
		winKernel.attachConsole(processID)
		res=winKernel.getStdHandle(STD_OUTPUT_HANDLE)
		if not res:
			raise OSError("NVDAObject_consoleWindowClassClient: could not get console std handle") 
		self.consoleHandle=res
		self.consoleEventHookHandles=[]
		self.oldLines=self.visibleLines
		textBuffer.NVDAObject_editableTextBuffer.__init__(self,*args)

	def __del__(self):
		try:
			winKernel.freeConsole()
		except:
			debug.writeException("freeConsole")
		NVDAObject_edit.__del__(self)

	def consoleEventHook(self,handle,eventID,window,objectID,childID,threadID,timestamp):
		self._reviewCursor=self.caretPosition
		newLines=self.visibleLines
		if eventID!=EVENT_CONSOLE_UPDATE_SIMPLE:
			self.speakNewText(newLines,self.oldLines)
		self.oldLines=newLines
		num=winKernel.getConsoleProcessList((ctypes.c_int*2)(),2)
		if num<2:
			winKernel.freeConsole()



	def getConsoleVerticalLength(self):
		info=winKernel.getConsoleScreenBufferInfo(self.consoleHandle)
		return info.consoleSize.y

	def getConsoleHorizontalLength(self):
		info=winKernel.getConsoleScreenBufferInfo(self.consoleHandle)
		return info.consoleSize.x

	def _get_visibleRange(self):
		info=winKernel.getConsoleScreenBufferInfo(self.consoleHandle)
		top=self.getPositionFromCoord(0,info.windowRect.top)
		bottom=self.getPositionFromCoord(0,info.windowRect.bottom+1)
		return (top,bottom)

	def _get_caretPosition(self):
		info=winKernel.getConsoleScreenBufferInfo(self.consoleHandle)
		y=info.cursorPosition.y
		x=info.cursorPosition.x
		return self.getPositionFromCoord(x,y)

	def _get_endPosition(self):
		return self.getConsoleVerticalLength()*self.getConsoleHorizontalLength()

	def getPositionFromCoord(self,x,y):
		return (y*self.getConsoleHorizontalLength())+x

	def getLineStart(self,pos):
		return pos-(pos%self.getConsoleHorizontalLength())

	def getLineNumber(self,pos):
		return pos/self.getConsoleHorizontalLength()

	def getLine(self,pos):
		maxLen=self.getConsoleHorizontalLength()
		lineNum=self.getLineNumber(pos)
		line=winKernel.readConsoleOutputCharacter(self.consoleHandle,maxLen,0,lineNum)
		if line.isspace():
			line=None
		else:
			line=line.rstrip()
		return line

	def _get_lineCount(self):
		return self.getConsoleVerticalLength()

	def getLineLength(self,pos):
		return self.getConsoleHorizontalLength()

	def _get_text(self):
		maxLen=self.endPosition
		text=winKernel.readConsoleOutputCharacter(self.consoleHandle,maxLen,0,0)
		return text

	def _get_visibleLines(self):
		visibleRange=self.visibleRange
		visibleRange=(self.getLineNumber(visibleRange[0]),self.getLineNumber(visibleRange[1]))
		lines=[]
		for lineNum in range(visibleRange[0],visibleRange[1]+1):
			line=self.getLine(self.getPositionFromCoord(0,lineNum))
			if line:
				lines.append(line)
		return lines

	def _get_value(self):
		return ""

	def event_gainFocus(self):
		time.sleep(0.1)
		self.cConsoleEventHook=ctypes.CFUNCTYPE(ctypes.c_voidp,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_int)(self.consoleEventHook)
		for eventID in [EVENT_CONSOLE_CARET,EVENT_CONSOLE_UPDATE_REGION,EVENT_CONSOLE_UPDATE_SIMPLE,EVENT_CONSOLE_UPDATE_SCROLL]:
			handle=winUser.setWinEventHook(eventID,eventID,0,self.cConsoleEventHook,0,0,0)
			if handle:
				debug.writeMessage("NVDAObject_consoleWindowClassClient: registered event: %s, handle %s"%(eventID,handle))
				self.consoleEventHookHandles.append(handle)
			else:
				raise OSError('Could not register console event %s'%eventID)
		audio.speakObjectProperties(typeString="console")
		for line in self.visibleLines:
			audio.speakText(line)

	def event_looseFocus(self):
		for handle in self.consoleEventHookHandles:
			winUser.unhookWinEvent(handle)

	def event_nameChange(self):
		pass

	def event_valueChange(self):
		pass

	def speakNewText(self,newLines,oldLines):
		diffLines=filter(lambda x: x[0]!="?",list(difflib.ndiff(oldLines,newLines)))
		for lineNum in range(len(diffLines)):
			if (diffLines[lineNum][0]=="+") and (len(diffLines[lineNum])>=3):
				if (lineNum>0) and (diffLines[lineNum-1][0]=="-") and (len(diffLines[lineNum-1])>=3):
					newText=""
					block=""
					diffChars=list(difflib.ndiff(diffLines[lineNum-1][2:],diffLines[lineNum][2:]))
					for charNum in range(len(diffChars)):
						if (diffChars[charNum][0]=="+"):
							block+=diffChars[charNum][2]
						elif block:
							audio.speakText(block)
							block=""
					if block:
						audio.speakText(block)
				else:
					audio.speakText(diffLines[lineNum][2:])

class NVDAObject_richEdit(ITextDocument.NVDAObject_ITextDocument,NVDAObject_MSAA):

	def __init__(self,*args):
		NVDAObject_MSAA.__init__(self,*args)
		ITextDocument.NVDAObject_ITextDocument.__init__(self,*args)

	def getDocumentObjectModel(self):
		domPointer=ctypes.POINTER(comtypes.automation.IDispatch)()
		res=ctypes.windll.oleacc.AccessibleObjectFromWindow(self.hwnd,OBJID_NATIVEOM,ctypes.byref(domPointer._iid_),ctypes.byref(domPointer))
		if res==0:
			return comtypesClient.wrap(domPointer)
		else:
			raise OSError("No ITextDocument interface")

	def _duplicateDocumentRange(self,rangeObj):
		return rangeObj.Duplicate

class NVDAObject_mozillaUIWindowClass(NVDAObject_MSAA):
	"""
	Based on NVDAObject, but on focus events, actions are performed whether or not the object really has focus.
	mozillaUIWindowClass objects sometimes do not set their focusable state properly.
	"""

	def event_gainFocus(self):
		self.speakObject()

class NVDAObject_mozillaUIWindowClass_application(NVDAObject_mozillaUIWindowClass):
	"""
	Based on NVDAObject_mozillaUIWindowClass, but:
	*Value is always empty because otherwise it is a long url to a .shul file that generated the mozilla application.
	*firstChild is the first child that is not a tooltip or a menu popup since these don't seem to allow getNext etc.
	*On focus events, the object is not spoken automatically since focus is given to this object when moving from one object to another.
	"""

	def _get_value(self):
		return ""

	def _get_firstChild(self):
		try:
			children=self.ia.accChildren()
		except:
			return None
		for child in children:
			try:
				role=child.role
				if role not in [ROLE_SYSTEM_TOOLTIP,ROLE_SYSTEM_MENUPOPUP]:
					return getNVDAObjectByAccessibleObject(child)
			except:
				pass

	def event_gainFocus(self):
		pass

class NVDAObject_mozillaContentWindowClass(NVDAObject_MSAA):
	pass

class NVDAObject_mozillaDocument(NVDAObject_MSAA):

	def _get_value(self):
		return ""

class NVDAObject_mozillaHeading(NVDAObject_MSAA):

	def _get_typeString(self):
		return _("heading")+" %s"%self.role[1]

class NVDAObject_mozillaListItem(NVDAObject_MSAA):

	def _get_name(self):
		child=NVDAObject_MSAA.getFirstChild(self)
		if child and child.Role==ROLE_SYSTEM_STATICTEXT:
 			return child.Name

	def _get_firstChild(self):
		child=super(NVDAObject_mozillaListItem,self).firstChild
		if child and child.role==ROLE_SYSTEM_STATICTEXT:
			child=child.next
		return child

class NVDAObject_link(NVDAObject_MSAA):
	"""
	Based on NVDAObject_MSAA, but:
	*Value is always empty otherwise it would be the full url.
	*typeString is link, visited link, or same page link depending on certain states.
	*getChildren does not include any text objects, since text objects are where the name of the link comes from.
	"""

	def _get_value(self):
		return ""

	def _get_typeString(self):
		states=self.states
		typeString=""
		if states&STATE_SYSTEM_TRAVERSED:
			typeString+="visited "
		if states&STATE_SYSTEM_SELECTABLE:
			typeString+="same page "
		typeString+=super(NVDAObject_link,self).typeString
		return typeString

	def _get_firstChild(self):
		child=super(NVDAObject_link,self).firstChild
		while child and (child.role in [ROLE_SYSTEM_STATICTEXT,ROLE_SYSTEM_TEXT]):
			child=child.next
		return child

class NVDAObject_mozillaText(textBuffer.NVDAObject_editableTextBuffer,NVDAObject_MSAA):
	"""
	Based on NVDAObject_mozillaContentWindowClass but:
	*If the object has a name but no value, the name is used as the value and no name is provided.
	*the role is changed to static text if it has the read only state set.
	"""

	def __init__(self,*args):
		NVDAObject_MSAA.__init__(self,*args)
		textBuffer.NVDAObject_editableTextBuffer.__init__(self,*args)

	def _get_name(self):
		name=super(NVDAObject_mozillaText,self).name
		value=super(NVDAObject_mozillaText,self).value
		if (self.role==ROLE_SYSTEM_STATICTEXT) and name and not value:
			return ""
		else:
			return name

	def _get_role(self):
		if super(NVDAObject_mozillaText,self).states&STATE_SYSTEM_READONLY:
			return ROLE_SYSTEM_STATICTEXT
		else:
			return super(NVDAObject_mozillaText,self).role
 
	def _get_value(self):
		name=super(NVDAObject_mozillaText,self).name
		value=super(NVDAObject_mozillaText,self).value
		if (self.role==ROLE_SYSTEM_STATICTEXT) and name and not value:
			return name
		else:
			return ""

	def _get_text(self):
		return self.value

class NVDAObject_listItem(NVDAObject_MSAA):

	def __init__(self,*args):
		NVDAObject_MSAA.__init__(self,*args)
		self.allowedNegativeStates=self.allowedNegativeStates|STATE_SYSTEM_SELECTED
		self._lastNegativeStates=self.calculateNegativeStates()

class NVDAObject_internetExplorerPane(NVDAObject_MSAA):

	def _get_value(self):
		return ""

