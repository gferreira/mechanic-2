from AppKit import *
import json
import logging
import time

import vanilla
from defconAppKit.windows.baseWindow import BaseWindowController

from mojo.extensions import getExtensionDefault, setExtensionDefault

from mechanic2.ui.cells import MCExtensionCirleCell, MCImageTextFieldCell
from mechanic2.ui.formatters import MCExtensionDescriptionFormatter
from mechanic2.ui.settings import Settings, extensionStoreDataURL
from mechanic2.extensionItem import ExtensionRepository, ExtensionStoreItem, ExtensionYamlItem
from mechanic2.mechanicTools import getDataFromURL


from lib.tools.debugTools import ClassNameIncrementer

class MyObject(NSObject, metaclass=ClassNameIncrementer):
   pass

logger = logging.getLogger("Mechanic")


class MCExtensionListItem(NSObject, metaclass=ClassNameIncrementer):

    def __new__(cls, *args, **kwargs):
        return cls.alloc().init()

    def __init__(self, extensionObject=None):
        self._extensionObject = extensionObject

    def copyWithZone_(self, zone):
        new = self.__class__.allocWithZone_(zone).init()
        new._extensionObject = self._extensionObject
        return new

    def extensionController(self):
        return self

    def extensionObject(self):
        return self._extensionObject

    def extensionSearchString(self):
        return self._extensionObject.extensionSearchString()


def getExtensionData(url):
    try:
        extensionData = getDataFromURL(url, formatter=json.loads)
    except Exception as e:
        logger.error("Cannot read url '%s'" % url)
        logger.error(e)
        extensionData = dict()
    return extensionData.get("extensions", [])


class MechanicController(BaseWindowController):

    def __init__(self, checkForUpdates=False, shouldLoad=False):

        self.w = vanilla.Window((800, 600), "Mechanic 2.1", minSize=(600, 400))

        # toolbar

        self._toolbarSearch = vanilla.SearchBox((0, 0, 300, 0), callback=self.toolbarSearch)
        self._toolbarSearch.getNSSearchField().setFrame_(((0, 0), (300, 22)))

        toolbarItems = [
            dict(
                itemIdentifier="search",
                label="Search",
                view=self._toolbarSearch.getNSSearchField(),
            ),
            dict(itemIdentifier=NSToolbarFlexibleSpaceItemIdentifier),
            dict(
                itemIdentifier="settings",
                label="Settings",
                imageNamed="prefToolbarMisc",
                callback=self.toolbarSettings,
            ),
        ]

        self.w.addToolbar(toolbarIdentifier="MechanicToolbar", toolbarItems=toolbarItems, addStandardItems=False, displayMode="icon")

        # extension list

        columnDescriptions = [
            dict(title="", key="extensionController", width=25, cell=MCExtensionCirleCell.alloc().init(), editable=False),
            dict(title="Extension", key="extensionController",
                cell=MCImageTextFieldCell.alloc().init(),
                formatter=MCExtensionDescriptionFormatter.alloc().init(),
                editable=False),
        ]

        extensionsGroup = vanilla.Group((0, 0, -0, -0))
        extensionsGroup.extensionList = vanilla.List((0, 0, 0, -40),
            [],
            columnDescriptions=columnDescriptions,
            showColumnTitles=False,
            selectionCallback=self.extensionListSelectionCallback,
            doubleClickCallback=self.extensionListDoubleClickCallback,
            allowsMultipleSelection=True,
            rowHeight=39,
            drawFocusRing=False,
        )
        extensionsGroup.extensionList.setSelection([])

        # bottom bar

        extensionsGroup.checkForUpdates = vanilla.Button((10, -30, 160, 22), "Check For Updates", callback=self.checkForUpdatesCallback, sizeStyle="small")

        extensionsGroup.purchaseButton  = vanilla.Button((10, -30, 100, 22), "Purchase", callback=self.purchaseCallback)
        extensionsGroup.installButton   = vanilla.Button((10, -30, 100, 22), "Install", callback=self.installCallback)
        extensionsGroup.uninstallButton = vanilla.Button((10, -30, 120, 22), "Uninstall", callback=self.uninstallCallback)
        extensionsGroup.updateButton    = vanilla.Button((10, -30, 110, 22), "Update", callback=self.updateCallback)

        allButtons = [extensionsGroup.purchaseButton, extensionsGroup.installButton, extensionsGroup.uninstallButton, extensionsGroup.updateButton]
        for button in allButtons:
            button.show(False)

        # streams

        streamsGroup = vanilla.Group((0, 0, -0, -0))
        streamsGroup.streamsLabel = vanilla.TextBox((0, 0, -0, -0), 'my streams', sizeStyle='small')
        streamsGroup.streamsList  = vanilla.List((0, 20, -0, -40), ["my precious", "testing", "pretty", "buggy"], allowsEmptySelection=True, drawFocusRing=False)
        # streamsGroup.streamsList.getNSTableView().setUsesAlternatingRowBackgroundColors_(False)
        streamsGroup.streamsList.getNSTableView().setSelectionHighlightStyle_(NSTableViewSelectionHighlightStyleSourceList)
        streamsGroup.addStream = vanilla.SquareButton((10, -30, 28, 20), "+")
        streamsGroup.removeStream = vanilla.SquareButton((37, -30, 28, 20), "-")

        # filters

        developersGroup = vanilla.Group((0, 0, -0, -0))
        developersGroup.developersLabel = vanilla.TextBox((0, 0, -0, -0), 'developers', sizeStyle='small')
        developersGroup.developersList  = vanilla.List((0, 20, -0, -0), [], drawHorizontalLines=False, drawFocusRing=False, selectionCallback=self.filtersCallback)
        developersGroup.developersList.getNSTableView().setUsesAlternatingRowBackgroundColors_(False)
        # developersGroup.developersList.getNSTableView().setSelectionHighlightStyle_(NSTableViewSelectionHighlightStyleSourceList)

        tagsGroup = vanilla.Group((0, 0, -0, -0))
        tagsGroup.tagsLabel = vanilla.TextBox((0, 0, -0, -0), 'tags', sizeStyle='small')
        tagsGroup.tagsList  = vanilla.List((0, 20, -0, -0), [], drawHorizontalLines=False, drawFocusRing=False, selectionCallback=self.filtersCallback)
        tagsGroup.tagsList.getNSTableView().setUsesAlternatingRowBackgroundColors_(False)
        # tagsGroup.tagsList.getNSTableView().setSelectionHighlightStyle_(NSTableViewSelectionHighlightStyleSourceList)

        sourcesGroup = vanilla.Group((0, 0, -0, -0))
        sourcesGroup.sourcesLabel = vanilla.TextBox((0, 0, -0, -0), 'sources', sizeStyle='small')
        sourcesGroup.sourcesList  = vanilla.List((0, 20, -0, -0), [], drawHorizontalLines=False, drawFocusRing=False, selectionCallback=self.filtersCallback)
        sourcesGroup.sourcesList.getNSTableView().setUsesAlternatingRowBackgroundColors_(False)
        # sourcesGroup.sourcesList.getNSTableView().setSelectionHighlightStyle_(NSTableViewSelectionHighlightStyleSourceList)

        # split views

        filtersGroup = vanilla.SplitView(
            (0, -0, -0, -0),
            paneDescriptions=[
                dict(view=developersGroup, identifier="developers"),
                dict(view=tagsGroup, identifier="tags"),
                dict(view=sourcesGroup, identifier="sources"),
            ],
            dividerStyle='thin')

        mainPanes = vanilla.SplitView(
            (0, 0, -0, -0),
            paneDescriptions=[
                dict(view=filtersGroup, identifier="filters", size=160, minSize=160, maxSize=240),
                dict(view=extensionsGroup, identifier="extensions"),
            ],
            isVertical=False,
            dividerStyle='thin')

        self.w.splitView = vanilla.SplitView(
            (0, 0, -0, -0),
            paneDescriptions=[
                dict(view=streamsGroup, identifier="streams", size=140, minSize=120, maxSize=200),
                dict(view=mainPanes, identifier="main"),
            ],
            isVertical=True,
            dividerStyle='thin')

        self._extensionsGroup = extensionsGroup
        self._developersGroup = developersGroup
        self._tagsGroup = tagsGroup
        self._sourcesGroup = sourcesGroup

        self.w.open()

        self._didCheckedForUpdates = False
        if shouldLoad:
            self.loadExtensions(checkForUpdates)

    def loadExtensions(self, checkForUpdates=False):
        progress = self.startProgress("Loading extensions...")

        wrappedItems = []

        allDevelopers = []
        allTags = []
        allSources = []

        # load extension streams
        for urlStream in getExtensionDefault("com.mechanic.urlstreams"):
            allSources.append(urlStream)

            clss = ExtensionRepository
            if urlStream == extensionStoreDataURL:
                clss = ExtensionStoreItem

            for data in getExtensionData(urlStream):
                try:
                    item = MCExtensionListItem(clss(data, checkForUpdates=checkForUpdates))
                    wrappedItems.append(item)

                    allDevelopers.append(data['developer'])
                    allTags += data['tags']

                except Exception as e:
                    logger.error("Creating extension item '%s' from url '%s' failed." % (data.get("extensionName", "unknow"), urlStream))
                    logger.error(e)

        # load single extension items
        for singleExtension in getExtensionDefault("com.mechanic.singleExtensionItems"):
            try:
                data = ExtensionYamlItem(singleExtension, checkForUpdates=checkForUpdates)
                item = MCExtensionListItem(data)
                wrappedItems.append(item)
            except Exception as e:
                logger.error("Creating single extension item '%s' failed." % singleExtension.get("extensionName", "unknow"))
                logger.error(e)

        # update UI list
        progress.update("Setting Extensions...")
        try:
            self._extensionsGroup.extensionList.set(wrappedItems)
            self._developersGroup.developersList.set(sorted(list(set(allDevelopers))))
            self._tagsGroup.tagsList.set(sorted(list(set(allTags))))
            self._sourcesGroup.sourcesList.set(allSources)

        except Exception as e:
            logger.error("Cannot set items in mechanic list.")
            logger.error(e)

        if checkForUpdates:
            progress.update("Checking for updates...")
            progress.setTickCount(len(wrappedItems))
            for item in wrappedItems:
                progress.update()
                item.extensionObject().extensionNeedsUpdate()
            progress.setTickCount(None)
            now = time.time()
            setExtensionDefault("com.mechanic.lastUpdateCheck", now)
            title = time.strftime("Checked at %H:%M", time.localtime(now))
            self._extensionsGroup.checkForUpdates.setTitle(title)
            self._didCheckedForUpdates = True
        progress.close()

    def extensionListSelectionCallback(self, sender):
        items = self.getSelection()
        multiSelection = len(items) > 1

        notInstalled = [item for item in items if not item.isExtensionInstalled()]
        installed = [item for item in items if item.isExtensionInstalled()]
        needsUpdate = [item for item in installed if item.extensionNeedsUpdate()]
        notInstalledStore = [item for item in notInstalled if item.isExtensionFromStore()]
        notInstalledNotStore = [item for item in notInstalled if not item.isExtensionFromStore()]

        buttons = []

        if notInstalledStore:
            title = "Purchase"
            if multiSelection:
                title += " (%s)" % len(notInstalledStore)
            buttons.append((title, self._extensionsGroup.purchaseButton))

        if notInstalledNotStore:
            title = "Install"
            if multiSelection:
                title += " (%s)" % len(notInstalledNotStore)
            buttons.append((title, self._extensionsGroup.installButton))

        if needsUpdate:
            title = "Update"
            if multiSelection:
                title += " (%s)" % len(needsUpdate)
            buttons.append((title, self._extensionsGroup.updateButton))

        if installed:
            title = "Uninstall"
            if multiSelection:
                title += " (%s)" % len(installed)
            buttons.append((title, self._extensionsGroup.uninstallButton))

        allButtons = [
            self._extensionsGroup.purchaseButton,
            self._extensionsGroup.installButton,
            self._extensionsGroup.uninstallButton,
            self._extensionsGroup.updateButton
        ]

        left = -10
        for title, button in buttons:
            button.show(True)
            _, top, width, height = button.getPosSize()
            button.setPosSize((left - width, top, width, height))
            button.setTitle(title)
            left -= width + 10
            allButtons.remove(button)

        for button in allButtons:
            button.show(False)

    def extensionListDoubleClickCallback(self, sender):
        items = self.getSelection()
        multiSelection = len(items) > 1
        for item in items:
            item.openRemoteURL(multiSelection)

    # buttons

    def checkForUpdatesCallback(self, sender):

        def _checkForUpdatesCallback(value):
            if value:
                if NSEvent.modifierFlags() & NSAlternateKeyMask:
                    # only check the selected items
                    items = self.getSelection()
                    progress = self.startProgress("Updating %s extensions..." % len(items))
                    progress.setTickCount(len(items))
                    for item in items:
                        progress.update()
                        item.forceCheckExtensionNeedsUpdate()
                    progress.setTickCount(None)
                    progress.close()
                    self._extensionsGroup.extensionList.getNSTableView().reloadData()
                    self.extensionListSelectionCallback(self._extensionsGroup.extensionList)
                else:
                    # load all extension and check for updates
                    self.loadExtensions(True)

        if self._didCheckedForUpdates:
            self.showAskYesNo("Check for updates, again?", "All extensions have been checked not so long ago.", callback=_checkForUpdatesCallback)
        else:
            _checkForUpdatesCallback(True)

    def purchaseCallback(self, sender):
        items = self.getSelection()
        multiSelection = len(items) > 1
        items = [item for item in items if item.isExtensionFromStore() and not item.isExtensionInstalled()]
        for item in items:
            item.openRemotePurchaseURL(multiSelection)

    def installCallback(self, sender):
        items = self.getSelection()
        items = [item for item in items if not item.isExtensionFromStore() and not item.isExtensionInstalled()]
        if not items:
            return
        self._extensionAction(items=items, message="Installing extensions...", action="remoteInstall")

    def uninstallCallback(self, sender):
        items = self.getSelection()
        items = [item for item in items if item.isExtensionInstalled()]
        if not items:
            return
        hasStoreItems = any([item.isExtensionFromStore() for item in items])
        if hasStoreItems:
            def callback(response):
                if response:
                    self._extensionAction(items=items, message="Uninstalling extensions...", action="extensionUninstall")
            purchasedItems = [item.extensionName() for item in items if item.isExtensionFromStore()]
            self.showAskYesNo("Uninstalling a purchased extension.", "Do you want to uninstall a purchased extensions: %s." % (", ".join(purchasedItems)), callback=callback)
        else:
            self._extensionAction(items=items, message="Uninstalling extensions...", action="extensionUninstall")

    def updateCallback(self, sender):
        items = self.getSelection()
        items = [item for item in items if item.isExtensionInstalled() and item.extensionNeedsUpdate()]
        if not items:
            return
        self._extensionAction(items=items, message="Updating extensions...", action="remoteInstall")

    def _extensionAction(self, items, message, action, **kwargs):
        multiSelection = len(items) > 1
        progress = self.startProgress(message)
        if multiSelection:
            progress.setTickCount(len(items))
        foundErrors = False
        for item in items:
            callback = getattr(item, action)
            try:
                callback(**kwargs)
            except Exception as e:
                print("Could not execute: '%s'. \n\n%s" % (action, e))
                foundErrors = True
            progress.update()
        progress.close()
        self._extensionsGroup.extensionList.getNSTableView().reloadData()
        self.extensionListSelectionCallback(self._extensionsGroup.extensionList)
        if foundErrors:
            self.showMessage(message, "Failed, see output window for details.")

    def settingsCallback(self, sender):
        self.loadExtensions()

    # toolbar

    def toolbarSettings(self, sender):
        Settings(self.w, callback=self.settingsCallback)

    def toolbarSearch(self, sender):
        search = sender.get()
        arrayController = self._extensionsGroup.extensionList.getNSTableView().dataSource()
        if not search:
            arrayController.setFilterPredicate_(None)
        else:
            searches = search.lower().strip().split(" ")
            query = []
            for search in searches:
                query.append('extensionSearchString CONTAINS "%s"' % search)
            query = " AND ".join(query)
            predicate = NSPredicate.predicateWithFormat_(query)
            arrayController.setFilterPredicate_(predicate)

    # filters

    def filtersCallback(self, sender):
        developers = self._developersGroup.developersList.get()
        tags = self._tagsGroup.tagsList.get()
        sources = self._sourcesGroup.sourcesList.get()

        searchDevelopers = [developers[i].lower() for i in self._developersGroup.developersList.getSelection()]
        searchTags = [tags[i] for i in self._tagsGroup.tagsList.getSelection()]
        searchSources = [sources[i] for i in self._sourcesGroup.sourcesList.getSelection()]

        arrayController = self._extensionsGroup.extensionList.getNSTableView().dataSource()
        if not (searchDevelopers or searchTags or searchSources):
            arrayController.setFilterPredicate_(None)

        else:
            searchDevelopers = [developers[i].lower() for i in self._developersGroup.developersList.getSelection()]
            searchTags = [tags[i] for i in self._tagsGroup.tagsList.getSelection()]
            # searchSources = [sources[i] for i in self._sourcesGroup.sourcesList.getSelection()]

            queryDevelopers = [f'extensionSearchString CONTAINS "{s}"' for s in searchDevelopers]
            queryTags = [f'extensionSearchString CONTAINS "{s}"' for s in searchTags]
            # querySources = [f'extensionSearchString CONTAINS "{s}"' for s in searchSources]

            queries = []
            for q in [queryDevelopers, queryTags]: # querySources
                if not q:
                    continue
                queries.append(f'({" OR ".join(q)})')

            query = " AND ".join(queries) if len(queries) > 1 else queries[0]
            print(query)

            predicate = NSPredicate.predicateWithFormat_(query)
            arrayController = self._extensionsGroup.extensionList.getNSTableView().dataSource()
            arrayController.setFilterPredicate_(predicate)

    # helpers

    def getSelection(self):
        arrayController = self._extensionsGroup.extensionList.getNSTableView().dataSource()
        selection = arrayController.selectedObjects()
        if selection:
            return [item.extensionObject() for item in selection]
        return []


if __name__ == '__main__':

    MechanicController(shouldLoad=True)
