"""
Janela responsável pela classe inicial do programa, MainFrame.
main_frame.py
"""

import os
import wx
from wx.core import Colour
import wx.lib.platebtn as pb
import wx.lib.scrolledpanel as scrolled
import sound
import settings
import json
import helper

class MainFrame(wx.Panel):
    def __init__(self, parent, folderPath):
        super().__init__(parent)

        self.parent = parent
        self.path = folderPath
        self.images = []        # Contém os paths das imagens da pasta
        self.widgets = []       # (btnRef, sizerRefs, btnCoordinates)
        self.ctrls = []         # Widgets que exibem ou recebem dados (wx.Slider, wx.TextCtrl, wx.ComboBox)
        self.buttons = []       # Irá conter os dados de buttons.json
        self.data = []          # Irá conter os dados de data.json
        self.lastStatus = {}    # Irá conter os valores de todo o sistema antes da mudança de valor.
        self.index = 0

        self.sound = sound.SoundManager()
        self.report = helper.Report(self)

        self.isInitMax = False
        self.isSoundActive = True
        self.tooltipContent = 0     # 0 para valor da medição, 1 para descrição
        self.isEquipZoom = False    # Se a imagem atualmente exibida é de algum 'zoom'.

        self.settingsWindow = None

        self.initUI()
        self.getButtons()
        self.OnValueChanged(None)
        self.getSystemStatus()

        self.Bind(wx.EVT_SIZE, self.OnResizing)
        self.SetDoubleBuffered(True)

        self.updateButtonTooltips()
        self.LoadConfigFile()

        if self.isInitMax:
            self.Maximize()

        self.parent.Centre()

    def initUI(self):
        ''' Inicializa a UI. '''

        self.SetBackgroundColour((171, 171, 171, 255))

        self.mainSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.imageSizer = wx.BoxSizer(wx.VERTICAL)

        self.scrolledSizer = wx.BoxSizer(wx.VERTICAL)
        self.scrolled = scrolled.ScrolledPanel(self, -1, style=wx.SUNKEN_BORDER)
        self.scrolled.SetMinSize((190, 600))
        self.scrolled.SetSizer(self.scrolledSizer)
        self.scrolled.Show(False)
        self.scrolled.SetupScrolling(scroll_x=False)
        self.scrolledSizer.Add( wx.StaticText(self.scrolled, -1, 'Painel de Controle'), flag=wx.ALIGN_CENTER | wx.ALL, border=10)
        self.scrolled.SetBackgroundColour('#f0f0f0')

        self.bitmap = None
        self.image = None
        self.image_aspect = None

        self.bmpImage = wx.StaticBitmap(self, wx.ID_ANY)

        self.mainSizer.Add(self.scrolled, 1, wx.EXPAND)
        self.imageSizer.Add(self.bmpImage, 1, wx.EXPAND)
        self.mainSizer.Add(self.imageSizer, 9, wx.EXPAND)

        self.images = self.getFolderImages(f'{self.path}')

        self.SetSizerAndFit(self.mainSizer)
        self.frameImage(self.images[self.index])

    def LoadConfigFile(self):
        ''' Carrega o arquivo com as configurações e as aplica. '''

        frame = settings.Settings(self)
        frame.Destroy()

    def getButtons(self):
        ''' Popula a lista `self.widgets`. '''

        with open(f"{self.path}/buttons.json", 'r', encoding='utf-8') as f:
            text = f.read()
            self.buttons = json.loads(text)

        with open(f"{self.path}/data.json", 'r', encoding='utf-8') as f:
            text = f.read()
            self.data = json.loads(text)

        for dic in self.buttons:
            b = pb.PlateButton(self.bmpImage, 1000 + dic['index'], style=pb.PB_STYLE_NOBG, name=dic['jsonKey'], size=((129, 30)))
            b.Bind(wx.EVT_BUTTON, self.OnButton)
            b.SetBitmap(wx.Bitmap(f"images/buttons/0_{dic['buttonName']}.png"))

            s = helper.ItemFrame(self.scrolled, self, dic)
            self.scrolledSizer.Add(s, flag=wx.ALL | wx.ALIGN_CENTER, border=10)

            # (btnRef, sizerRef, btnCoordinates)
            self.widgets.append((b, s, dic['coordinates']))

    def getSystemStatus(self):
        ''' Guarda o estado de todo o sistema, como o nome dos equipamentos e valores, no dicionário `self.lastStatus`. '''

        self.lastStatus.clear()
        for ctrl in self.ctrls:
            self.lastStatus[ctrl.GetName()] = ctrl.GetValue()

    def OnButton(self, event):
        ''' Chamada quando um botão é clicado. '''

        obj = event.GetEventObject()
        ID = obj.GetId() - 1000

        if self.widgets[ID][1].IsShown():
            self.widgets[ID][1].Hide()
        else:
            self.widgets[ID][1].Show()

        self.updateScrolledVisibility()
        self.frameImage(self.images[self.index], True)

    def updateScrolledVisibility(self):
        ''' Atualiza a visibilidade do self.scrolled. '''

        isAnyShown = []
        for i in range (0, len(self.widgets)):
            isAnyShown.append(self.widgets[i][1].IsShown())

        if any(isAnyShown):
            self.scrolled.Show(True)
        else:
            self.scrolled.Show(False)

    def showButtons(self, show):
        ''' Mostra ou esconde todos os botoões da imagem. '''

        for d in self.widgets:
            btn = d[0]
            btn.Show(show)

    def updateButtons(self):
        ''' Atualiza a posição dos botões na tela. '''

        sizerDim = self.imageSizer.GetSize()
        sizer_aspect = sizerDim[0] / sizerDim[1]

        for btn in self.widgets:
            button_horizontal = int(sizerDim[0] * btn[2][self.index][0])
            button_vertical = int(sizerDim[1] * btn[2][self.index][1])

            if self.image_aspect <= sizer_aspect:
                # Frame is wider than image so find the horizontal white space size to add
                image_width = sizerDim[1] * self.image_aspect
                horizontal_offset = (sizerDim[0] - image_width) / 2
                button_horizontal = int(horizontal_offset + image_width * btn[2][self.index][0])

            elif self.image_aspect > sizer_aspect:
                # Frame is higher than image so find the vertical white space size to add
                image_height = sizerDim[0] / self.image_aspect
                vertical_offset = (sizerDim[1] - image_height) / 2
                button_vertical = int(vertical_offset + image_height * btn[2][self.index][1])

            btn[0].Position = (button_horizontal, button_vertical)

    def replaceImage(self, index, path):
        ''' Substitui a imagem em `index` pela imagem (`path`) na lista `self.images`. '''

        self.images[index] = path
        if not self.isEquipZoom:
            self.frameImage(self.images[self.index])

    def frameImage(self, path, isJustResize=False):
        ''' Recebe o path da imagem e atualiza na tela. '''

        if not isJustResize:
            self.bitmap = wx.Bitmap(path, wx.BITMAP_TYPE_ANY)
            self.image = wx.Bitmap.ConvertToImage(self.bitmap)
            self.image_aspect = self.image.GetSize()[0] / self.image.GetSize()[1]

        self.Layout()   # Para atualizar o tamanho do self.imageSizer

        image_width, image_height = self.imageSizer.GetSize()
        new_image_width = image_width
        new_image_height = int(new_image_width / self.image_aspect)

        if new_image_height > image_height:
            new_image_height = image_height
            new_image_width = int(new_image_height * self.image_aspect)

        image = self.image.Scale(new_image_width, new_image_height)

        self.Freeze()
        self.bmpImage.SetBitmap(image.ConvertToBitmap())
        self.Thaw()     # Freeze() e Thaw() previne flickering.

        self.Layout()
        self.updateButtons()

    def getFolderImages(self, path):
        ''' Recebe uma string com o caminho da pasta e retorna uma lista com os paths de todas as imagens da pasta. '''

        jpgs = [f for f in os.listdir(path) if f[-4:] == ".JPG"]
        return [os.path.join(path, f) for f in jpgs]

    def OnValueChanged(self, event):
        ''' Chamada quando o valor em qualquer um dos botões é modificado. '''

        values = []

        # Pega os valores dos widgets que o usuário pode modificar o valor.
        for i in range(0, len(self.buttons)):
            dic = {}
            if self.buttons[i]['isControllable']:
                key = self.buttons[i]['jsonKey']
                dic['key'] = key
                dic['value'] = self.ctrls[i].GetValue()
                values.append(dic)

                dic = {}

        # Encontra no data.json o index corresponde aos dados dos widgets.
        index = -1
        hook = 'rpm'
        for dic in values:
            # Usaremos um "anzol" para pegar todos os outros dados.
            if dic['key'] == hook:
                for i in range(0, len(self.data)):
                    if int(dic['value']) == self.data[i][hook][1]:
                        index = i
                        break

        for dic in values:
            if dic['key'] != hook:
                for i in range(index, len(self.data)):
                    key = dic['key']
                    if int(dic['value']) == self.data[i][key]:
                        index = i
                        break

        self.refreshOnDisplayValues(index)
        self.updateButtonTooltips()

        if event:
            self.updateSoundPlay()
            self.report.TakeNote(self.lastStatus, event.GetEventObject())
            self.getSystemStatus()

    def refreshOnDisplayValues(self, index):
        ''' Recebe um `index` do índice no arquivo data.json que contém os dados que deverá ser exibido em um widget. '''

        self.dataIndex = index
        for i in range(0, len(self.buttons)):
            if not self.buttons[i]['isControllable']:
                key = self.widgets[i][0].GetName()
                value = str(self.data[index][key])
                self.ctrls[i].SetValue(value)

    def OnClosePanel(self, event):
        ''' Chamada quando o botão de fechar dentro de um `ItemFrame` for clicado. '''

        obj = event.GetEventObject()
        ID = obj.GetId() - 1000

        self.widgets[ID][1].Hide()

        self.updateScrolledVisibility()
        self.frameImage(self.images[self.index], True)

    def OnNext(self, event):
        ''' Quando o usuário clica para ir para a próxima imagem. '''

        if not self.isEquipZoom:
            self.index += 1
        else:
            self.isEquipZoom = False

        if self.index >= len(self.images):
            self.index = 0

        self.frameImage(self.images[self.index])
        self.showButtons(True)

    def OnPrevious(self, event):
        ''' Quando o usuário clica para voltar para a imagem anterior. '''

        if not self.isEquipZoom:
            self.index -= 1
        else:
            self.isEquipZoom = False

        if self.index < 0:
            self.index = len(self.images) - 1

        self.frameImage(self.images[self.index])
        self.showButtons(True)

    def OnResizing(self, event):
        ''' Chamada quando o usuário '''

        self.frameImage(self.images[self.index], True)
        event.Skip()

    def OnSettings(self, event):
        ''' Abre a janela de configurações. '''

        if not self.settingsWindow:
            self.settingsWindow = settings.Settings(self)
            self.settingsWindow.Show()

    def OnReport(self, event):
        ''' Mostra a janela de relatorio. '''

        if not self.report.IsShown():
            self.report.Show()

    def OnClearReport(self, event):
        ''' Limpa a janela do relatório. '''

        self.report.ClearScrolled()

    def OnEquip(self, event):
        ''' Chamada quando o usuário clica para ver um dos equipamentos, seja pela toolbar ou menu. '''

        ID = event.GetId()
        try:
            name = event.GetEventObject().GetToolShortHelp(ID)
        except:
            name = event.GetEventObject().GetLabel(ID)

        self.frameImage(f'{self.path}/misc/{name}.jpg')
        self.showButtons(False)
        self.isEquipZoom = True

    def updateButtonStyle(self, style):
        ''' Muda o estilo dos botões. '''

        if style == 'Fundo transparente':
            style = pb.PB_STYLE_NOBG
        elif style == 'Cor gradiente':
            style = pb.PB_STYLE_GRADIENT
        elif style == 'Bordas redondas':
            style = pb.PB_STYLE_DEFAULT
        elif style == 'Bordas quadradas':
            style = pb.PB_STYLE_SQUARE
        else:
            return

        # (btnRef, sizerRef, btnCoordinates)
        for button in self.widgets:
            button[0]._style = style

        self.bmpImage.Refresh(False)

    def updateButtonHoverColor(self, new_color):
        ''' Atualiza a cor de fundo (hover) dos botões. '''

        color = Colour(new_color)
        for button in self.widgets:
            button[0].SetPressColor(Colour(color))

        self.bmpImage.Refresh(False)

    def updateButtonBackgroundColor(self, color):
        ''' Atualiza a cor de fundo dos botões. '''

        if color == 'Azul':
            index = 1
        else:
            index = 0

        for i in range (0, len(self.buttons)):
            dic = self.buttons[i]
            self.widgets[i][0].SetBitmap(wx.Bitmap(f"images/buttons/{index}_{dic['buttonName']}.png"))

        self.bmpImage.Refresh(False)

    def updateButtonTooltips(self):
        ''' Atualiza o conteúdo das tooltips do botões de acordo com self.tooltipContent.
        0 para valor da medição, 1 para descrição. '''

        if self.tooltipContent == 0:
            dic = self.data[self.dataIndex]
            for i in range(0, len(self.widgets)):
                key = self.widgets[i][0].GetName()
                value = dic[key]
                unit = self.buttons[i]['unit']

                index = unit.find(']')
                if index != -1:
                    unit = unit[index + 2:]

                self.widgets[i][0].SetToolTip(f"{value} {unit}")

        else:
            for i in range(0, len(self.widgets)):
                self.widgets[i][0].SetToolTip(self.buttons[i]['description'])

    def updateSoundPlay(self):
        ''' Atualiza o estado do som da motor elétrico, se pode tocar ou não. '''

        rpm = int(self.ctrls[2].GetValue())         # ctrls[2] -> 'Motor Elétrico'
        registro = int(self.ctrls[0].GetValue())    # ctrls[0] -> 'Registro Esfera'
        isWaterFlowing = rpm > 0 and registro > 0

        if isWaterFlowing:
            self.replaceImage(0, f'{self.path}/misc/0_water.jpg')
        else:
            self.replaceImage(0, f'{self.path}/0.JPG')

        if self.isSoundActive:
            if rpm > 0:
                self.sound.SoundPlayback('rpm', True)
            else:
                self.sound.SoundPlayback('rpm', False)

            if isWaterFlowing:
                self.sound.SoundPlayback('abertura', True)
            else:
                self.sound.SoundPlayback('abertura', False)

        else:
            self.sound.SoundPlayback('rpm', False)
            self.sound.SoundPlayback('abertura', False)

    def updateSoundVolume(self, newVolume):
        ''' Atualiza o volume do som. '''

        self.sound.SoundVolume(newVolume)

    def updateIsInitMaxVariable(self, new_value):
        ''' Atualiza o valor de self.isInitMax. '''

        self.isInitMax = new_value

    def updateIsSoundActiveVariable(self, new_value):
        ''' Atualiza o valor de self.isSoundActive. '''

        self.isSoundActive = new_value

class Init(wx.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        self.SetIcon(wx.Icon('images/icons/app_logo.ico'))
        self.SetTitle('Laboratório Virtual de Bombas Hidráulicas')
        self.SetMinSize((1200, 700))

        self.frame = MainFrame(self, 'data/system1')

        self.statusBar = self.CreateStatusBar()
        self.menu = wx.MenuBar()
        self.initMenu()
        self.toolbar = self.CreateToolBar()
        self.initToolbar()
        self.Bind(wx.EVT_CHAR_HOOK, self.OnKey)

        self.frame.Show()
        self.Centre()

    def initToolbar(self):
        ''' Inicializa a toolbar. '''

        left_arrow = self.toolbar.AddTool(wx.ID_ANY, 'Left', wx.Bitmap('images/icons/left.png'), 'Anterior')
        right_arrow = self.toolbar.AddTool(wx.ID_ANY, 'Right', wx.Bitmap('images/icons/right.png'), 'Próxima')
        settings = self.toolbar.AddTool(wx.ID_ANY, 'Settings', wx.Bitmap('images/icons/settings.png'), 'Configurações')
        self.toolbar.AddSeparator()

        motor =  self.toolbar.AddTool(1000, 'Motor Elétrico', wx.Bitmap('images/icons/motor.png'), 'Motor Elétrico')
        bomba =  self.toolbar.AddTool(1001, 'Bomba', wx.Bitmap('images/icons/water_pump.png'), 'Bomba')
        registro =  self.toolbar.AddTool(1002, 'Registro Esfera', wx.Bitmap('images/icons/registro_esfera.png'), 'Registro Esfera')
        vazao =  self.toolbar.AddTool(1003, 'Medidor de Vazão', wx.Bitmap('images/icons/medidor_de_vazao.png'), 'Medidor de Vazão')
        manovac =  self.toolbar.AddTool(1004, 'Manovacuômetro', wx.Bitmap('images/icons/manovacuometro.png'), 'Manovacuômetro')
        mano =  self.toolbar.AddTool(1005, 'Manômetro', wx.Bitmap('images/icons/manometro.png'), 'Manômetro')
        piezometro =  self.toolbar.AddTool(1006, 'Piezômetro', wx.Bitmap('images/icons/piezometro.png'), 'Piezômetro')

        self.Bind(wx.EVT_TOOL, self.frame.OnNext, right_arrow)
        self.Bind(wx.EVT_TOOL, self.frame.OnPrevious, left_arrow)
        self.Bind(wx.EVT_TOOL, self.frame.OnSettings, settings)

        self.Bind(wx.EVT_TOOL, self.frame.OnEquip, motor)
        self.Bind(wx.EVT_TOOL, self.frame.OnEquip, bomba)
        self.Bind(wx.EVT_TOOL, self.frame.OnEquip, registro)
        self.Bind(wx.EVT_TOOL, self.frame.OnEquip, vazao)
        self.Bind(wx.EVT_TOOL, self.frame.OnEquip, manovac)
        self.Bind(wx.EVT_TOOL, self.frame.OnEquip, mano)
        self.Bind(wx.EVT_TOOL, self.frame.OnEquip, piezometro)

        self.toolbar.Realize()

    def initMenu(self):
        ''' Inicializa o menu. '''

        # Menu 'Arquivo'
        fileMenu = wx.Menu()
        left = fileMenu.Append(-1, 'Anterior')
        right = fileMenu.Append(-1, 'Próxima')
        settings = fileMenu.Append(-1, 'Configurações')
        fileMenu.AppendSeparator()
        leave = fileMenu.Append(wx.ID_EXIT, 'Sair')

        # Menu Relatório
        reportMenu = wx.Menu()
        openReport = reportMenu.Append(-1, 'Abrir relatório')
        clearReport = reportMenu.Append(-1, 'Limpar relatório')

        # Menu 'Equipamentos'
        equipMenu = wx.Menu()
        bomba = equipMenu.Append(-1, 'Bomba')
        motor = equipMenu.Append(-1, 'Motor Elétrico')
        registro = equipMenu.Append(-1, 'Registro Esfera')
        vazao = equipMenu.Append(-1, 'Medidor de Vazão')
        manovac = equipMenu.Append(-1, 'Manovacuômetro')
        mano = equipMenu.Append(-1, 'Manômetro')
        piezometro = equipMenu.Append(-1, 'Piezômetro')

        # Menu 'Ajuda'
        ajudaMenu = wx.Menu()
        tutorial = ajudaMenu.Append(-1, 'Iniciar tutorial')
        sobre = ajudaMenu.Append(wx.ID_ABOUT, 'Sobre')

        # Bindings
        self.Bind(wx.EVT_MENU, self.frame.OnPrevious, left)
        self.Bind(wx.EVT_MENU, self.frame.OnNext, right)
        self.Bind(wx.EVT_MENU, self.frame.OnReport, openReport)
        self.Bind(wx.EVT_MENU, self.frame.OnClearReport, clearReport)
        self.Bind(wx.EVT_MENU, self.frame.OnSettings, settings)
        self.Bind(wx.EVT_MENU, self.OnCloseApp, leave)

        self.Bind(wx.EVT_MENU, self.frame.OnEquip, motor)
        self.Bind(wx.EVT_MENU, self.frame.OnEquip, bomba)
        self.Bind(wx.EVT_MENU, self.frame.OnEquip, registro)
        self.Bind(wx.EVT_MENU, self.frame.OnEquip, vazao)
        self.Bind(wx.EVT_MENU, self.frame.OnEquip, manovac)
        self.Bind(wx.EVT_MENU, self.frame.OnEquip, mano)
        self.Bind(wx.EVT_MENU, self.frame.OnEquip, piezometro)

        self.menu.Append(fileMenu, '&Arquivo')
        self.menu.Append(reportMenu, '&Relatório')
        self.menu.Append(equipMenu, '&Equipamentos')
        self.menu.Append(ajudaMenu, 'Ajuda')

        self.SetMenuBar(self.menu)

    def OnKey(self, event):
        ''' Captura teclas. '''

        if event.GetKeyCode() == wx.WXK_LEFT:
            self.frame.OnPrevious(None)

        elif event.GetKeyCode() == wx.WXK_RIGHT:
            self.frame.OnNext(None)

    def OnCloseApp(self, event):
        ''' Fecha o app. '''

        self.Destroy()

app = wx.App()
frame = Init(None)
frame.Show()
app.MainLoop()