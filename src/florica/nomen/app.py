# ruff: noqa: E402

#add icon.names in _icons.qrc then
#pyrcc5 _ressources.qrc -o src/florica/core/resources.py


import os
#os.environ["QT_LOGGING_RULES"] = "qt.qpa.*=false"

import sys

# Standard library
import json
import re
import time
# Third-party
from PyQt5 import QtCore, QtGui, QtWidgets
from florica.core import resources  # noqa: F401
#import taxa_occ.core.ressources

# Internal modules
from florica.core import functions

from florica.models.taxa_model import (
    PNTaxa_searchAPI, PNTaxa_treeModel, PNTaxa, PNTaxa_with_Score, 
    PNTaxa_QTreeView, PNTaxa_add, PNTaxa_edit, PNTaxa_merge,
    PNSynonym, PNSynonym_edit
)
from florica.core.widgets import PN_JsonQTreeView, LinkDelegate, PostgresConfigDialog, load_ui_from_resources, MessageBox, ConfigManager   #, PN_DatabaseStatusWidget
from florica.core.database import DatabaseConnection, PN_dbTaxa

#generic function to access to the dbases classes
#access to the postgresql connexion
def db_postgres():
    """DBASE: returns the instance of the open db connexion (DatabaseConnection)"""
    return functions.db()
#access to a postgres connexion with specific procedures for taxa management
def db_taxa():
    """DBASE: returns the instance of the open dbtaxa connexion (PN_dbTaxa)"""
    return functions.dbtaxa()

#Class _EditProperties_Delegate is used by the MainWindow class to edit the properties of the PN_JsonQTreeView
class _EditProperties_Delegate(QtWidgets.QStyledItemDelegate):
    """
    A custom delegate class for editing properties in a PN_JsonQTreeView.

    This class is responsible for creating editors for specific columns in the tree view,
    based on the type of data in the dict_properties dictionary (for the moment qlinedit and combobox)

    Attributes:
        None

    Methods:
        createEditor: Creates an editor (QLineEdit or QComboBox) for a specific column.
        setEditorData: Sets the data for the editor.
        setModelData: Saves the data from the editor into the model.
    """
    def __init__(self, dict_properties, parent=None):
        super().__init__(parent)
        self.db_properties = dict_properties

    def createEditor(self, parent, option, index):
        """ Create the editor (QlineEdit or ComboBox) according to type in the dict_properties         
        """
        if index.column() == 1:
            #get the columns name and value
            try:
                field_table = index.parent().data(0).lower()
                field_name = index.siblingAtColumn(0).data().lower()
                field_value = index.siblingAtColumn(1).data()
                field_def = self.db_properties[field_table][field_name]
            except Exception:
                field_def = None
                return
            if field_def is None : 
                return
            #do not edit value with brackets (convention)
            if re.search(r'\[.*\]',field_value): 
                return
            _type = field_def.get("type", 'text')
            _lsitems = field_def.get("items", None)
            if _type == 'text' and _lsitems is None :
                editor = QtWidgets.QLineEdit(parent)
            else:
                editor = QtWidgets.QComboBox(parent)
                if _lsitems:
                    editor.addItems(_lsitems)
                elif _type == 'boolean':
                    editor.addItems(['True', 'False'])
                editor.addItems(['Unknown'])
            return editor        
        return

    def setEditorData(self, editor, index):
        """ Fill the editor with the model value"""
        if index.column() == 1:
            data = index.model().data(index, QtCore.Qt.DisplayRole)
            if isinstance(editor, QtWidgets.QLineEdit):
                editor.setText(str(data))
            elif isinstance(editor, QtWidgets.QComboBox):
                if not data:
                    data = 'Unknown'
                editor.setCurrentText(str(data))

    def setModelData(self, editor, model, index):
        """ Save the value into the model """

        if index.column() == 1:
            if isinstance(editor, QtWidgets.QLineEdit):
                _value = editor.text()
            elif isinstance(editor, QtWidgets.QComboBox):
                _value = editor.currentText()
                if _value == 'Unknown':
                    _value = ''
            # if model.data(index) != _value:
            #     model.setData(index.siblingAtColumn(0), font, QtCore.Qt.FontRole)
            model.setData(index, _value)

#class _MetadataDelegateWithAuthorCheck is used to highlight the authors name in red if it does not match the current authors name
#surcharging the LinkDelegate used to highlight the hyperlinks in the metadata treeview
class _MetadataDelegateWithAuthorCheck(LinkDelegate):
    menu_action_triggered = QtCore.pyqtSignal(str, str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self._authors_name = None
        self._button_rects = {}
        self.menuclipboard = QtWidgets.QMenu(parent)
        font = QtGui.QFont()
        font.setPointSize(10)
        self.menuclipboard.setFont(font)
        #actions list
        actions = ["Copy Value", "Copy Key-Value"]
        for i, text in enumerate(actions):
            act = self.menuclipboard.addAction(text)
            act.setData(i)  # stocke l'index de l'action
            act.triggered.connect(lambda checked=False, a=act.text(): self._triggerClipboard(a))
        self._current_index = 0
        # resize menu
        fm = QtGui.QFontMetrics(font)
        max_width = fm.horizontalAdvance("Copy Key-Value") + 60  # marge
        self.menuclipboard.setFixedWidth(max_width)

    def set_authors_name(self, name):
        self._authors_name = name

    def paint(self, painter, option, index):
        # Apply the superclass's paint method (web links)
        super().paint(painter, option, index)

        # Additional logic for column 1 and key
        if index.column() == 1:
            key = index.sibling(index.row(), 0).data(QtCore.Qt.DisplayRole)
            value = index.data(QtCore.Qt.DisplayRole)
            if key == "Authors" and value != self._authors_name:
                # paint foreground in red if authors are different
                option.palette.setColor(option.palette.Text, QtGui.QColor("red"))
                super().paint(painter, option, index)  # repaint in red
            elif value == 'No results':
                # paint foreground in red if authors are different
                option.palette.setColor(option.palette.Text, QtGui.QColor("red"))
                super().paint(painter, option, index)  # repaint in red

            if (
                    (option.state & QtWidgets.QStyle.State_Selected)
                    and index.parent().isValid()
                ):
                    self.drawButton(painter, option, index)

    def drawButton(self, painter, option, index):
    # create a button for edition
        r = option.rect
        rect = QtCore.QRect(r.right() - 22, r.top(), 20, r.height())
        self._button_rects[index] = rect

        # create a button for edition
        opt = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)        
        opt.text = "⋮"
        opt.rect = rect
        opt.displayAlignment = QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter

        # no icon, no decoration, only two points
        opt.features &= ~QtWidgets.QStyleOptionViewItem.HasDecoration
        option.widget.style().drawControl(
            QtWidgets.QStyle.CE_ItemViewItem,
            opt,
            painter,
            option.widget
        )

    def editorEvent(self, event, model, option, index):
    #manage the mouse clic to produce an event
        if event.type() == QtCore.QEvent.MouseButtonPress:
            rect = self._button_rects.get(index)
            if rect and rect.contains(event.pos()):
                self._current_index = index
                self.menuclipboard.exec_(QtGui.QCursor.pos())
                return True
        return super().editorEvent(event, model, option, index)

    def _triggerClipboard(self, action_text):
    #copy option into the clipboard
        index = self._current_index
        if index is None:
            return
        clipboard = QtWidgets.QApplication.clipboard()
        key = index.sibling(index.row(), 0).data(QtCore.Qt.DisplayRole)
        value = index.sibling(index.row(), 1).data(QtCore.Qt.DisplayRole)
        if action_text == "Copy Value":
            clipboard.setText(str(value))
        elif action_text == "Copy Key-Value":
            clipboard.setText(f"{key} - {value}")

#class _TaxonomyProxyModel is used for filtering the Taxonomy TreeView according to the checkboxes
class _TaxonomyProxyModel(QtCore.QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        # --- Filter parameters
        self.show_checked_mode = 1  # 1: All, 2: True, 3: False
        self.show_published_mode = 1
        self.show_accepted_mode = 1
        self.children_only = False

    def match_filter(self, mode, value):
    # Method for match logic
        if mode == 1:
            return True
        if mode == 2:
            return bool(value)
        return not bool(value)
    
    def childCount(self):
    # the number of visible child nodes in the proxy model (populated root nodes)
        total_child_count = 0
        for row in range(self.rowCount()):
            root_index = self.index(row, 0, QtCore.QModelIndex())
            if root_index.isValid():
                total_child_count += self.rowCount(root_index)
        return total_child_count
    
    def nodeMatchesFilters(self, node):
    #return true/false according to the filters
        return all([
            self.match_filter(self.show_checked_mode, getattr(node, 'taxaname_score', None)),
            self.match_filter(self.show_published_mode, getattr(node, 'published', False)),
            self.match_filter(self.show_accepted_mode, getattr(node, 'accepted', False)),
        ])

    def filterAcceptsRow(self, source_row: int, source_parent: QtCore.QModelIndex) -> bool:
    # filter node visibility, return True/False according to filters
        index = self.sourceModel().index(source_row, 0, source_parent)
        if not index.isValid():
            return False        
        node = index.data(QtCore.Qt.UserRole)
        if index.parent().isValid():
            return self.nodeMatchesFilters (node)
        # if not children_only root node is visible
        if not self.children_only:
            return True        
        return self.hasAcceptedChildren(index)

    def hasAcceptedChildren(self, parent_index):
    #return True if a child node of parent_index is visible according to filters
        model = self.sourceModel()
        for row in range(model.rowCount(parent_index)):
            child_index = model.index(row, 0, parent_index)
            if not child_index.isValid():
                continue
            node = child_index.data(QtCore.Qt.UserRole)
            if self.nodeMatchesFilters (node):
                return True
        return False


##The MainWindow load the ui interface to navigate and edit taxaname###
class MainWindow(QtWidgets.QMainWindow):
    """
    This class represents the main window of the application and is responsible for managing the user interface. 
    Provide properties to manage the UI elements.
    """

    toolbox_click = QtCore.pyqtSignal(int)
    def __init__(self):
        super().__init__()
        # load the GUI
        self.window = load_ui_from_resources("taxanames.ui")
        self._ui_enabled = True

    # setting the widgets links to ui
        self.trview_taxonref = self.window.main_treeView
        self.button_metadata_refresh = self.window.button_metadata_refresh
        self.buttonbox_filter = self.window.buttonBox_filter
        self.buttonbox_filter_apply = self.window.buttonBox_filter.button(QtWidgets.QDialogButtonBox.Apply)
        self.buttonbox_filter_reset = self.window.buttonBox_filter.button(QtWidgets.QDialogButtonBox.Reset)

        self.button_properties = self.window.buttonBox_identity
        self.button_properties_apply = self.button_properties.button(QtWidgets.QDialogButtonBox.Apply)
        self.button_properties_cancel = self.button_properties.button(QtWidgets.QDialogButtonBox.Cancel)
        self.button_reference_add = self.window.button_reference_add
        self.button_reference_edit = self.window.button_reference_edit
        self.button_reference_remove = self.window.button_reference_remove
        self.button_reference_merge = self.window.button_reference_merge
        self.button_synonym_add = self.window.button_synonym_add
        self.button_synonym_edit = self.window.button_synonym_edit
        self.button_synonym_remove = self.window.button_synonym_remove
        self.button_rankgroup = self.window.button_rankGroup
        self.button_themes = self.window.button_themes
        self.button_showFilter = self.window.button_showFilter

        self.checkBox_published = self.window.checkBox_published
        self.checkBox_accepted = self.window.checkBox_accepted
        self.checkBox_children = self.window.checkBox_withtaxa
        self.checkBox_checked = self.window.checkBox_checked
        self.searchtaxon = self.window.lineEdit_searchtaxon
        self.toolBox = self.window.toolBox
        self.combo_taxa = self.window.combo_taxa

    #setting the filter checkboxes to partially checked
        self.checkBox_published.setCheckState(QtCore.Qt.PartiallyChecked)
        self.checkBox_accepted.setCheckState(QtCore.Qt.PartiallyChecked)
        self.checkBox_children.setCheckState(QtCore.Qt.PartiallyChecked)
        self.checkBox_checked.setCheckState(QtCore.Qt.PartiallyChecked)

    #set the buttons icons
        self.buttonbox_filter_apply.setIcon (QtGui.QIcon(":src/florica/resources/icons/ok.png"))
        self.buttonbox_filter_reset.setIcon (QtGui.QIcon(":src/florica/resources/icons/refresh.png"))
        self.button_properties_apply.setIcon (QtGui.QIcon(":src/florica/resources/icons/ok.png"))
        self.button_properties_cancel.setIcon (QtGui.QIcon(":src/florica/resources/icons/nok.png"))

    #set the toolbox icon style
        index = self.toolBox.currentIndex()
        self._on_toolbox_click(index)
    
    #add two labels to displayed msg in the statusbar
        self.selected_rank_label = QtWidgets.QLabel()
        self.selected_taxa_label = QtWidgets.QLabel()
        self.window.statusbar.addWidget(self.selected_rank_label)
        self.window.statusbar.addWidget(self.selected_taxa_label)
        self.window.statusBar().addPermanentWidget(self.button_themes)
        self.toolBox.currentChanged.connect(self._on_toolbox_click)

    def _on_toolbox_click(self, index):
        #set the icons to the toolbox and emit a signal
        self.toolBox.setItemIcon(index, QtGui.QIcon(":src/florica/resources/icons/arrow2.png"))
        for i in range(3):
            if i != index:
                self.toolBox.setItemIcon(i, QtGui.QIcon(":src/florica/resources/icons/arrow1.png"))
        self.toolbox_click.emit(index)
    
    @property
    def ui_enabled(self) -> bool:
        """Get or set the enabled state of the ui (buttons, combo, checkbox)"""
        return self._ui_enabled
    @ui_enabled.setter
    def ui_enabled(self, enabled: bool):
        self._ui_enabled = enabled
        #set the enabled state of the ui
        self.button_synonym_add.setEnabled(enabled)
        self.button_synonym_edit.setEnabled(enabled)
        self.button_synonym_remove.setEnabled(enabled)
        self.button_reference_merge.setEnabled(enabled)
        self.button_reference_edit.setEnabled(enabled)
        self.button_reference_remove.setEnabled(enabled)
        self.button_metadata_refresh.setEnabled(enabled)
        self.button_reference_add.setEnabled(enabled)
        #major buttons
        self.button_showFilter.setEnabled(enabled)
        self.button_rankgroup.setEnabled(enabled)
        self.combo_taxa.setEnabled(enabled)
        self.checkBox_published.setEnabled(enabled)
        self.checkBox_accepted.setEnabled(enabled)
        self.checkBox_checked.setEnabled(enabled)
        self.checkBox_children.setEnabled(enabled)

    @property
    def buton_theme_text(self) -> str:
        """Get or set the text for the button themes"""
        return self.window.button_themes.text()
    @buton_theme_text.setter
    def buton_theme_text(self, text: str):
        self.window.button_themes.setText(text or "Default Style")

    @property
    def button_rank_text(self) -> str:
        """Get or set the text for the rank button"""
        return self.button_rankgroup.text()
    @button_rank_text.setter
    def button_rank_text(self, text: str):
        self.button_rankgroup.setText(text) 

    @property
    def button_filter_visible(self) -> bool:
        """Get or set the visibility of the filter Frame"""
        return self.window.frame_filter.isVisible()
    @button_filter_visible.setter
    def button_filter_visible(self, visible: bool):
        self.window.frame_filter.setVisible(visible)

    @property
    def label_rank(self) -> str:
        """Get or set the text for the label_rank"""
        return self.selected_rank_label.text()
    @label_rank.setter
    def label_rank(self, text: str):
        self.selected_rank_label.setText(text)

    @property
    def label_taxa(self) -> str:
        """Get or set the text for the label_taxa"""
        return self.selected_taxa_label.text()
    @label_taxa.setter
    def label_taxa(self, text: str):
        self.selected_taxa_label.setText(text)

    @property
    def label_count (self) -> str:
        """Get or set the text for the label_count"""
        return self.window.label_count.text()
    @label_count.setter
    def label_count (self, text: str):
        self.window.label_count.setText(text)

    @property
    def label_time (self) -> str:
        """Get or set the text for the label_query_time"""
        return self.window.label_query_time.text()
    @label_time.setter
    def label_time (self, text: str):
        self.window.label_query_time.setText(text)

    @property
    def search_taxon(self) -> str:
        """Get or set the text for the filter search_taxon"""
        return self.searchtaxon.text()
    @search_taxon.setter    
    def search_taxon(self, text: str):
        self.searchtaxon.setText(text)



class MainWindowController:
    """
        The controller class of the MainWindow class
        Initializes the MainWindowController object given a view object.
        It sets the view, window, connected status, db properties, authors delegate,
        config manager, and loads widgets from and to the view.
        It sets the filtering and sorting on the proxy model for trview_taxonref,
        creates the metadata worker (Qthread) and sets the slots signals.
    """    
#the main controller of the application
    def __init__(self, view):
        self.view = view
        self.window = self.view.window
        self.connected = False
        self.db_properties = None
        #self.view.set_filter_visible(False)
        self.view.button_filter_visible = False
        self.authors_delegate = _MetadataDelegateWithAuthorCheck()
        config_file = functions.resource_path("config.ini")
        self.config_manager = ConfigManager(config_file)

        #load widgets from the view
        self.trview_taxonref = view.trview_taxonref
        
        #load widgets to the view
        self.dbwidget = DatabaseConnection() #PN_DatabaseStatusWidget()
        self.window.statusBar().addPermanentWidget(self.dbwidget)

        self.trview_properties =  PN_JsonQTreeView ()
        layout = self.window.toolBox.widget(2).layout()
        layout.insertWidget(0,self.trview_properties) 

        self.trview_metadata = PN_JsonQTreeView ()
        layout = self.window.toolBox.widget(1).layout()
        layout.insertWidget(0,self.trview_metadata)

        self.trview_names = PN_JsonQTreeView ()
        layout = self.window.toolBox.widget(0).layout()
        layout.insertWidget(0,self.trview_names)

        self.trview_filter = PN_JsonQTreeView ()
        layout = self.window.frame_filter.layout()
        layout.insertWidget(1,self.trview_filter)

        self.trview_hierarchy = PNTaxa_QTreeView ()
        layout = self.window.trview_hierarchy_Layout
        layout.insertWidget(0,self.trview_hierarchy)
        
        self.combo_taxa = view.combo_taxa

         #set filtering and sorting on the proxymodel for trview_taxonref
        self.trview_taxonref.setSortingEnabled(True)
        self.trview_taxonref.header().setSortIndicator(0, QtCore.Qt.AscendingOrder)
        self.proxy_model = _TaxonomyProxyModel()
        self.proxy_model.setSourceModel(PNTaxa_treeModel())
        self.proxy_model.setDynamicSortFilter(True)
        self.proxy_model.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.trview_taxonref.setModel(self.proxy_model)
        
        #create the metadata worker (Qthread)
        self.metadata_worker = PNTaxa_searchAPI(view)

        self.trview_metadata.setItemDelegate(self.authors_delegate)

    #setting the slots signals
        #signals from menus clicked (theme and rank group)
        self.view.toolbox_click.connect(self.on_toolbox_clicked)
        #signals from buttons
        self.view.button_showFilter.toggled.connect(self.on_button_filter_clicked)  
        self.view.button_synonym_add.clicked.connect(self.on_button_synonym_add_clicked)
        self.view.button_synonym_edit.clicked.connect(self.on_button_synonym_edit_clicked)
        self.view.button_synonym_remove.clicked.connect(self.on_button_synonym_remove_clicked)
        self.view.button_reference_add.clicked.connect(self.on_button_reference_add_clicked)   
        self.view.button_reference_edit.clicked.connect(self.on_button_reference_edit_clicked)
        self.view.button_reference_remove.clicked.connect(self.on_button_reference_remove_clicked)
        self.view.button_reference_merge.clicked.connect(self.on_button_reference_merge_clicked)
        self.view.button_metadata_refresh.clicked.connect (self.on_button_metadata_clicked)
        self.view.button_properties_apply.clicked.connect(self.apply_edit_properties)
        self.view.button_properties_cancel.clicked.connect(self.on_button_properties_cancel_clicked)
        #signals from searchTaxon enter
        self.view.searchtaxon.returnPressed.connect(self.trview_taxonref_setData)
        #signals from checkboxes
        self.view.checkBox_published.stateChanged.connect(self.trview_taxonref_refreshData)
        self.view.checkBox_accepted.stateChanged.connect(self.trview_taxonref_refreshData)
        self.view.checkBox_children.stateChanged.connect(self.trview_taxonref_refreshData)
        self.view.checkBox_checked.stateChanged.connect(self.trview_taxonref_refreshData)
        #signals from trviews    
        self.trview_taxonref.selectionModel().selectionChanged.connect(self.on_trview_taxonref_clicked)
        self.trview_taxonref.doubleClicked.connect(self.on_trview_taxonref_dblclicked)
        self.trview_hierarchy.selectionModel().selectionChanged.connect(self.on_trview_hierarchy_clicked)
        self.trview_hierarchy.doubleClicked.connect(self.on_trview_hierarchy_dblclicked)
        self.trview_names.selectionModel().selectionChanged.connect(self.refresh_ui_trview_hierarchy)
        self.trview_properties.changed_signal.connect(self.refresh_ui_buttons_properties)
        
        self.metadata_worker.Result_Signal.connect(self.trview_metadata_setDataAPI)
        #self.combo_taxa.currentIndexChanged.connect(self.trview_taxonref_setData)
        self.dbwidget.clicked.connect(self.on_status_clicked)

        self.view.buttonbox_filter_apply.clicked.connect(self.trview_taxonref_setData)
        self.view.buttonbox_filter_reset.clicked.connect(self.on_button_filter_reset_clicked)
   #load themes menu
        button_themes_menu = QtWidgets.QMenu()
        menu_items = ["Adaptic", "Combinear", "Diffnes", "Geoo", "Lightstyle", "Obit"]

        for item in menu_items:
            action = QtWidgets.QAction(item, self.view)
            action.triggered.connect(lambda checked, item=item: self.on_menu_theme_clicked(item))
            button_themes_menu.addAction(action)
        self.view.button_themes.setMenu(button_themes_menu)
    #load the grouped ranks menu
        menu_button_rankGroup = QtWidgets.QMenu()
        # create an exclusive action group for menu
        action_group = QtWidgets.QActionGroup(self.view)
        action_group.setExclusive(True)
        actions = []
        # set the list of the available ranks
        menu_items = ['Subregnum','Division', 'Classis', 'Subclassis', 'Order', 'Family', 'Genus']
        for item in menu_items:
            action = QtWidgets.QAction(item, self.view)
            action.setCheckable(True)
            action_group.addAction(action)
            actions.append(action)
            action.triggered.connect(lambda checked, item=item: self.on_menu_rank_clicked(item))
            menu_button_rankGroup.addAction(action)
        #set the family as default selected item
        self.view.button_rankgroup.setMenu(menu_button_rankGroup)
        _selected_item = 5
        actions[_selected_item].setChecked(True)
        #self.view.set_rankgroup_text(menu_items[_selected_item])
        self.view.button_rank_text = menu_items[_selected_item]

    @property
    def trview_taxonref_selectedItem(self):
        """GUI: Return the current selectedItem (class PNTaxa_with_Score) in the trview_taxonref"""
        proxy_index = self.trview_taxonref.currentIndex()
        source_index = self.proxy_model.mapToSource(proxy_index)
        return self.proxy_model.sourceModel().data(source_index, QtCore.Qt.UserRole)
    @trview_taxonref_selectedItem.setter
    def trview_taxonref_selectedItem(self, id_taxonref):
        #select the item in the trview_taxonref with the id_taxonref
        model = self.proxy_model.sourceModel()
        index = model.indexItem(id_taxonref)
        index = self.proxy_model.mapFromSource(index)
        if index.isValid():
            self.trview_taxonref.selectionModel().setCurrentIndex(index, QtCore.QItemSelectionModel.ClearAndSelect | QtCore.QItemSelectionModel.Rows)        
        return
    
    @property
    def selectedItem(self):
        """GUI: return the current selectedItem (class PNTaxa_with_Score) in the trview_hierarchy""" 
        return self.trview_hierarchy.selecteditem()


    @property
    def selectedIdrank(self):
        """GUI: Returns the selected id_rank from the UI (button_rankGroup)"""
        group_text = self.view.button_rank_text
        idrankparent = db_taxa().db_get_rank(group_text, 'id_rank')
        if not idrankparent:
            idrankparent = 14 
        return idrankparent
    
    @property
    def selectedFilter(self):
        """
        GUI: Returns a dictionary of filters (db_dic_filter) from the UI (combo_taxa and trview_filter filters)
        """
        dict_filter = db_taxa().db_dic_filter
        #dict_filter["nb_filter"] = 0
        if self.combo_taxa.currentIndex() == -1:
            self.combo_taxa.setCurrentIndex(0)
        combo_taxa_index = self.combo_taxa.currentIndex()
        #search for a selected idtaxonref into the combo_taxa
        idtaxonref = self.combo_taxa.itemData(combo_taxa_index, role=QtCore.Qt.UserRole).idtaxonref
        if len(self.view.search_taxon) > 0:
            dict_filter["search_name"] = self.view.search_taxon
            #dict_filter["nb_filter"] +=1
        if idtaxonref == 0:
            idtaxonref = None
            if combo_taxa_index > 0:
                #add the selected clade to the filter
                dict_filter["clade"] = self.combo_taxa.currentText()
        else:
            dict_filter["id_taxonref"] = idtaxonref
            #dict_filter["nb_filter"] +=1
        #get the properties filter
        properties_filter = {}
        for key, value in self.trview_filter.dict_user_properties().items():
            for key2, value2 in value.items():
                if value2:
                    if key not in properties_filter:
                        properties_filter[key] = {}
                    properties_filter[key][key2] = value2
        if properties_filter:
            dict_filter["properties"] = properties_filter
            #dict_filter["nb_filter"] +=1
        #send the complete dict_filter
        #set the number of active filters, except clade
        #dict_filter["nb_filter"] = sum(v is not None and k!="clade" for k, v in dict_filter.items())
        return dict_filter


    @property
    def get_list_PNTaxa(self):
        """Return a list of objets (class PNTaxa_with_Score) from the database that match the selectedFilter"""
        #get the current filter
        dict_filter = self.selectedFilter
        nb_filter = sum(v is not None and k!="clade" for k, v in dict_filter.items())
        self.view.button_showFilter.setStyleSheet(
                "color: rgb(0, 55, 217);" if nb_filter else ""
        )
        #get the list of taxa resulting from a query in the database
        records = db_taxa().db_get_json_taxa(self.selectedIdrank, dict_filter)
        data = []
        #create the list of PNTaxa
        for rec in records:
            item = PNTaxa_with_Score(rec.get("id_taxonref"), rec.get("taxaname"), rec.get("authors"), 
                            rec.get("id_rank"), rec.get("published"), rec.get("accepted"))
            item.id_parent = rec.get("id_parent")
            #set the taxaname_score and authors_score 
            item.taxaname_score = rec.get("taxaname_score", None)
            item.authors_score = rec.get("authors_score", None)
            data.append(item)
        return data

    def on_button_filter_clicked(self, state: bool):
        """GUI : hide/show filter Frame according to the state of the button_showFilter"""
        #self.view.set_filter_visible(state)
        self.view.button_filter_visible = state

    def on_menu_rank_clicked(self, rank):
        """GUI : Fill data in the trview_taxonref according to the selected rank"""
        #clic on a rankGroup Menu item
        #self.view.set_rankgroup_text(rank)
        self.view.button_rank_text = rank
        self.trview_taxonref_setData()

    def on_menu_theme_clicked(self, item):
        """GUI : Change the global theme of the UI through qss"""
        if item is None:
            item = "Diffnes"
    #to change the theme        
        try:
            qss_path = f":src/florica/resources/qss/{item}.qss"
            file = QtCore.QFile(qss_path)
            if not file.open(QtCore.QIODevice.ReadOnly | QtCore.QIODevice.Text):
                raise RuntimeError(file.errorString())
            stream = QtCore.QTextStream(file)
            stylesheet = stream.readAll()
            file.close()
            QtWidgets.qApp.setStyleSheet(stylesheet)
            self.config_manager.theme = item
        except Exception as e:
            item = None
        #set the theme to the theme button
        self.view.buton_theme_text = item

    def on_status_clicked(self):
        """GUI: Load the database dialogBox to edit database parameters"""
        dlg = PostgresConfigDialog(self.config_manager, self.window)
        result = dlg.exec_()
        if not result:
            return
        self.database_open()

    def database_open(self):
        """GUI: Open the database from the config.ini file"""
        #self.view.set_ui_enabled(False)
        self.view.ui_enabled = False
    #disconnect signal and set the default value for combo_taxa        
        self.signal_combo_taxa(False)
        self.combo_taxa.clear()
        self.combo_taxa.addItem('All names')
        self.combo_taxa.setItemData(0, PNTaxa(0, 'All names', '', 0), role=QtCore.Qt.UserRole) 
    #load the connection, load dialog box if not connected
        while True:
            pg = self.config_manager.postgresql
            if pg:
                self.connected = self.dbwidget.open(pg)                
                if self.connected:
                    break
            dlg = PostgresConfigDialog(self.config_manager, self.window)
            result = dlg.exec_()
            if not result:
                break


    #return if not connected (or loop ??)
        if not self.connected:
            return
    #load the specific taxa database functions
        taxa = PN_dbTaxa(self.dbwidget)
    #initialize the registry database services
        functions._registry = None
        functions.init_registry(functions.ServiceRegistry(self.dbwidget, taxa=taxa))
    #set the APG options into self.combo_taxa
        lst = db_taxa().db_get_clades()
        for clade in lst:
            self.combo_taxa.addItem(clade)
            self.combo_taxa.setItemData(self.combo_taxa.count() - 1, PNTaxa(0, clade), role=QtCore.Qt.UserRole)
        self.combo_taxa.setCurrentIndex(0)
        #set delegate for editing properties of PN_trview_identity & PN_trview_filter
        self.db_properties = taxa.db_dic_properties
        delegate = _EditProperties_Delegate(self.db_properties)
        self.trview_properties.setItemDelegate(delegate)
        self.trview_filter.setItemDelegate(delegate)
        self.trview_properties.setEditTriggers(QtWidgets.QAbstractItemView.CurrentChanged)
        self.trview_filter.setEditTriggers(QtWidgets.QAbstractItemView.CurrentChanged)
        
        #set the delegate and slots signals
    #reconnect the signal to combo_taxa
        self.signal_combo_taxa(True)
        #self.combo_taxa.currentIndexChanged.connect(self.trview_taxonref_setData)
    #set the ui enabled for the general widgets 
        self.refresh_ui_trview_taxonref(True)
    #initialize the trview_taxonref (list of taxa)
        self.trview_filter_load()
        self.trview_taxonref_setData()


    def signal_combo_taxa (self, connected = True):
        """GUI: Set the connection signal status for combo_taxa"""
        try:
            self.combo_taxa.currentIndexChanged.disconnect()
        except Exception:
            pass
        if connected:
            self.combo_taxa.currentIndexChanged.connect(self.trview_taxonref_setData)


    


    def combo_taxa_selectedItem(self, selecteditem):
        """GUI: Select item into the combo_taxa (add if necessary)"""
        index = -1
        #disconnect the signal
        self.signal_combo_taxa(False)
        self.combo_taxa.setCurrentIndex(index)
        if selecteditem.id_rank >= 21:
            return
        #search for the item in the combo
        for i in range (self.combo_taxa.count()):
            if self.combo_taxa.itemData(i, role=QtCore.Qt.UserRole).idtaxonref == selecteditem.idtaxonref:
                index = i
                break
        #add new if not found
        if index == -1:
            self.combo_taxa.addItem(selecteditem.taxonref)
            index = self.combo_taxa.count() - 1
            self.combo_taxa.setItemData(index, selecteditem, role=QtCore.Qt.UserRole)
        #reconnect and select the item
        self.signal_combo_taxa(True)
        self.combo_taxa.setCurrentIndex(index)

    def combo_taxa_deletedItem(self, idtaxonref):
        """GUI: delete the selecteditem from the combo_taxa"""
        index = -1
        for i in range (self.combo_taxa.count()):
            if self.combo_taxa.itemData(i, role=QtCore.Qt.UserRole).idtaxonref == idtaxonref:
                index = i
                break
        if index != -1:
            self.combo_taxa.removeItem(index)

    def on_toolbox_clicked(self, index = None):
        """GUI : Set data into the tabs Names, Metadata and Properties"""
        #by default the currentindex
        if index is None:
            index = self.view.toolBox.currentIndex()
        #get the current selected item
        if self.selectedItem is None:
            return
        #set the authors name to the delegate
        new_authors_name = self.selectedItem.authors
        self.authors_delegate.set_authors_name(new_authors_name)
        if index == 2  and self.trview_properties.id != self.selectedItem.idtaxonref:
            self.trview_properties_setData()
            self.trview_properties.id = self.selectedItem.idtaxonref
        elif index == 1  and self.trview_metadata.id != self.selectedItem.idtaxonref:
            self.trview_metadata_setData()
            self.trview_metadata.id = self.selectedItem.idtaxonref
        elif index == 0 : 
            self.trview_names_setData()
            self.trview_names.id = self.selectedItem.idtaxonref

#functions for the trview
    def trview_filter_load(self):
        """GUI: Load the trview_filter with default values"""
        dict_db_properties = {}
        for _key, _value in self.db_properties.items():
            dict_db_properties[_key] = {}.fromkeys(_value,'')
        self.trview_filter.setData(dict_db_properties)


    def trview_metadata_setData(self):
        """GUI: Load the set of metadata to selectedItem from database"""
        if self.selectedItem is None:
            return
        dict_metadata = self.selectedItem.json_metadata
        if dict_metadata is None:
            dict_metadata = {}
        #set the query time stamps
        self.view.label_time = ''
        if dict_metadata.get("score", None):
            self.view.label_time = str(dict_metadata["score"].get("query_time", ''))
        # #sort the jsonb according to the list of api (sort and exclude score)
        list_api = self.metadata_worker.list_api
        dict_final = {}
        for key in list_api:
            if dict_metadata.get(key, None):
                dict_final[key] = dict_metadata.get(key, 'No results')
        #set the metadata data
        self.trview_metadata.setData (dict_final)


    def trview_names_setData(self):
        """GUI: Load the set of names to selectedItem from database"""
        if self.selectedItem is None:
            return
        self.trview_names.setData(self.selectedItem.json_names)
        self.refresh_ui_buttons_names()

    def trview_properties_setData(self):
        """GUI: Load the set of properties to selectedItem from database"""
        if self.selectedItem is None:
            return
        self.view.button_properties.setVisible(False)
        if self.selectedItem.id_rank < 21:
            identity_data = self.selectedItem.json_properties_count
            self.trview_properties.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            self.trview_properties.tab_header = ["Property", "Taxa count"]
        else:
            identity_data = self.selectedItem.json_properties
            self.trview_properties.setEditTriggers(QtWidgets.QAbstractItemView.CurrentChanged)
            self.trview_properties.tab_header = ["Property", "Value"]
            self.view.button_properties.setVisible(True)
        #set the properties and metadata
        self.trview_properties.setData(identity_data)
        # #conserve the selected idtaxonref 
        # self.trview_properties.id = self.selectedItem.idtaxonref

    def refresh_ui_buttons_properties(self, changed):
        """GUI: Refresh access to buttons linked to self.trview_properties"""
        self.view.button_properties.setEnabled(changed)

    def apply_edit_properties(self):
        """GUI: Updating reference properties in the database from trview_properties"""
        #return if no change to update
        if not self.trview_properties.changed():
            return
        self.refresh_ui_buttons_properties(False)
        #get the current id for editing
        id_taxonref = self.trview_properties.id
        #get the dictionnaries (db = input and user = output)
        dict_user_properties = self.trview_properties.dict_user_properties()
        #construct the dictionnary with non-null value
        tab_result = {}
        for key, value in dict_user_properties.items():
            tab_tmp = {}
            for _key, _value in value.items():
                if _value !='':
                    tab_tmp[_key]= _value
            if len(tab_tmp) > 0:
                tab_result[key] = tab_tmp
        #transform dictionnary to json
        _properties = None
        if tab_result:
            _properties = json.dumps(tab_result)
        #send the json to the database
        if not db_taxa().db_update_properties (id_taxonref, _properties):
            msg = db_postgres().postgres_error()
            MessageBox().information_msgbox("Error", msg, True)

    def on_trview_hierarchy_clicked(self):  
        """GUI: When clicked, load the properties, metadata and names of the selected item"""
        self.on_toolbox_clicked()
        self.refresh_ui_trview_hierarchy()

    def on_trview_hierarchy_dblclicked(self):
        """GUI: When double-licked, set the selectedItem as a filter in the combo_taxa"""
    #set the selecteditem to the filter combo_taxa
        if self.selectedItem is None:
            return
        self.combo_taxa_selectedItem(self.selectedItem)


        
    def trview_metadata_setDataAPI(self, base, api_json):
        """GUI: Set the metadata received from The Thread metaworker and save the json into the database when finish"""
        selecteditem = self.selectedItem
        _selecteditem = self.metadata_worker.PNTaxa_model
        _data_list = None
        if base == "NOTCONNECTED":
            msg = "Error: no connection to the internet"
            MessageBox().information_msgbox("Connection error", msg, True)  
            self.view.button_metadata_refresh.setEnabled(True)
            return
        elif base == "END":
            self.view.button_metadata_refresh.setEnabled(True)
            #metadata_worker.PNTaxa_model.json_request = None
            if api_json is None:
                return
            tab_synonyms =[]
            #decompose synonyms and metadata
            for taxa in api_json: 
                try:
                    tab_synonyms += api_json[taxa]["synonyms"]
                #to suppress synonyms from json before saving (do we save or not ? NOT)
                    #api_json[taxa].pop("synonyms")
                except Exception:
                    continue
            #add new synonyms into the dbase to the id_taxonref
            if tab_synonyms:
                new_synonyms = 0
                tab_synonyms = [taxa.strip() for taxa in tab_synonyms]
                unique_set = set(tab_synonyms)
                #add new synonyms names according to the previous query
                for taxa in unique_set: #new_unique_taxa:
                    dict_taxa = functions.get_dict_from_species(taxa)
                    if dict_taxa is None:
                        dict_taxa = {}
                        dict_taxa["names"] = [taxa]
                    for value in dict_taxa["names"]:
                        if db_taxa().db_add_synonym(_selecteditem.id_taxonref, value, 'Homotypic'):
                            new_synonyms += 1
                #refresh the tab names for the current selecteditem if newsynonyms
                if new_synonyms > 0 and self.selectedItem == _selecteditem:
                    self.trview_names_setData()             
            #manage and save json medata (including or not synonyms depends of the check line above)

        #update metadata
            _data_list = json.dumps(api_json)
            db_taxa().db_update_metadata (_selecteditem.id_taxonref, _data_list)

            if "score" in api_json:
                dict_score = api_json["score"]
                trview_item = self.proxy_model.sourceModel().getItem(_selecteditem.idtaxonref)
                if trview_item:
                    trview_item.taxaname_score = dict_score["taxaname_score"]
                    trview_item.authors_score = dict_score["authors_score"]
                self.trview_taxonref.repaint()
        else:
            self.view.button_metadata_refresh.setEnabled(False)

            #manage json in live ! coming from the metadata_worker api_thread, one by one
            if selecteditem != _selecteditem:
                return        
            if self.metadata_worker.status == 0:
                return
            if "score" in api_json:
                dict_score = api_json["score"]
                trview_item = self.proxy_model.sourceModel().getItem(_selecteditem.idtaxonref)
                if trview_item:
                    trview_item.taxaname_score = dict_score["taxaname_score"]
                    trview_item.authors_score = dict_score["authors_score"]
                del api_json["score"]
             #fill the treeview with the dictionnary json
            self.trview_taxonref.repaint()
            self.trview_metadata.dict_db_properties[base] = api_json
            self.trview_metadata.refresh()
        return


    def on_trview_taxonref_clicked(self):
        """GUI: On click, set the hierarchy of the selecteditem in trview_hierarchy"""
        #check if a previous changed has not be saved
        # check if the buttonbox_identity is enabled (if properties have been changed)
        if self.view.button_properties.isVisible() and self.view.button_properties.isEnabled():
                self.view.button_properties.setEnabled(False)
                msg = "Some properties have been changed, save the changes ?"
                result = MessageBox().question_msgbox ("Save properties", msg)
                if result:
                    self.apply_edit_properties()
        
        # get the current selectedItem      
        selecteditem = self.trview_taxonref_selectedItem #()
        if selecteditem is None:
            return
        #selecteditem.id_taxonref = 166666666
    #set the treetaxonomy hierarchy
        self.trview_hierarchy.setdata (selecteditem, selecteditem.id_taxonref)


    def on_trview_taxonref_dblclicked(self, current_index):
        """GUI: On Doubleclick, set the selecteditem as a filter in the combo_taxa"""
        # Select or insert the selecteditem into the combo_taxa combobox for shortcut
        #selecteditem = self.trview_taxonref.model().data(current_index, QtCore.Qt.UserRole)
        selecteditem = self.trview_taxonref_selectedItem #()
        if selecteditem:
            self.combo_taxa_selectedItem(selecteditem)

    # def trview_taxonref_refresh(self, dict_torefresh):
    #     return
    #     #selected_item = self.trview_taxonref_selectedItem #()
    #     self.trview_taxonref_setData()
    #     # id_taxonref = dict_torefresh[0]['id_taxonref']
    #     # self.trview_taxonref_selectedItem = selected_item.id_taxonref
    #     # model = self.proxy_model.sourceModel()
    #     # index = model.indexItem(selected_item.id_taxonref)
    #     # index = self.proxy_model.mapFromSource(index)
    #     # if index.isValid():
    #     #     self.trview_taxonref.selectionModel().setCurrentIndex(index, QtCore.QItemSelectionModel.ClearAndSelect | QtCore.QItemSelectionModel.Rows)        
    #     return

    # #refresh (update) the trview_taxonref model according to the database for a list of idtaxonref (refresh taxa + childs)
   
    #     model = self.proxy_model.sourceModel()
    #     self.view.set_taxa_label('< no selection >')
    #     print ('longueur du dict_torefresh, ',len(dict_torefresh))
    #     #filter dict_torefresh to conserve only taxa to refresh (include in the view area [grouped_idrank or higher] and with id_taxonref)
    #     #conserve only one item in a hierarchical dict_torefresh
    #     dict_parent = {item["id_taxonref"]: item for item in dict_torefresh}
    #     ls_idtaxonref = []
    #     for item in dict_torefresh:
    #         _idrank = item.get("id_rank", None)
    #         _idtaxonref = item.get("id_taxonref", None)
    #         _idparent = item.get("id_parent", None)
    #         #only concerned if _idrank is >= grouped_idrank and with id_taxonref
    #         if _idtaxonref and _idrank and _idrank >= self.get_idrankGroup():
    #             #only add if no parent in the list to refresh (to avoid to refresh multiple times the same branch in the treeview)
    #             if _idparent and dict_parent.get(_idparent, None) is None:
    #                 ls_idtaxonref.append(_idtaxonref)
    #     if not ls_idtaxonref:
    #         return []
               
    #     #create list to update and to remove in the model
    #     items_to_update = []
    #     items_toremove = []
    #     for id_taxonref in ls_idtaxonref:
    #         _lsitems = self.get_list_PNTaxa(id_taxonref, True)
    #         if _lsitems:
    #             items_to_update.extend(_lsitems)
    #         else:
    #             items_toremove.append(id_taxonref)
    #     print ('longueur de la liste à rafraichir, ',len(items_to_update))
    #     print ('longueur de la liste à remove, ',len(items_toremove))
    #     #get the id_taxonref childs from the  to remove in the model
    #     items_toremove = db_taxa().db_get_childs(items_toremove)
    #     #remove nodes in the model
    #     for item in items_toremove:
    #         model.removeItem(item)
    #     #disconnect the signals
    #     try:
    #         #disconnect signal to avoid multiple events (except error if not yet connected)
    #         self.trview_taxonref.selectionModel().selectionChanged.disconnect()
    #     except Exception:
    #         pass
    #     #select null parent
    #     self.trview_taxonref.setCurrentIndex(QtCore.QModelIndex())

        

    # #edit/add nodes in the model
    #     if items_to_update:   
    #         model.refresh(items_to_update)
    #         item = items_to_update[0]
    #         # _idtaxonref = item.id_taxonref
    #         # index = model.indexItem(_idtaxonref)
    #         # # #search for item index
    #         # # index = model.indexItem(item.id_taxonref)
    #         # # #search for the id_parent if index not valid
    #         # if not index.isValid():
    #         index = model.indexItem(item.id_taxonref)
    #         if not index.isValid():
    #             index = model.indexItem(item.id_parent)
    #         #get the index in the proxy model
    #         index = self.proxy_model.mapFromSource(index)
    #         if index.isValid():
    #             self.trview_taxonref.selectionModel().setCurrentIndex(index, QtCore.QItemSelectionModel.ClearAndSelect | QtCore.QItemSelectionModel.Rows)


    #     #reconnect the signal
    #     self.trview_taxonref.selectionModel().selectionChanged.connect(self.on_trview_taxonref_clicked)
    #     self.trview_taxonref.repaint()
    #     return items_to_update

    def trview_taxonref_setData(self):
        """GUI: Set the data to the trview_taxonref model from database"""
        #self.view.set_rank_label(f"Rank {self.view.button_rank_text}: ")
        self.view.label_rank = f"Rank {self.view.button_rank_text}: "
        # #disconnect the signals
        # try:
        #     #disconnect signal to avoid multiple events (except error if not yet connected)
        #     self.trview_taxonref.selectionModel().selectionChanged.disconnect()
        # except Exception:
        #     pass
        # clean the content and selection of trview_taxonref
        self.proxy_model.sourceModel().clear()
        #get the list of PNTaxa from dbase, according to filters
        data = self.get_list_PNTaxa
        #refresh the model with new data from dbase
        self.proxy_model.sourceModel().refreshData(data)
        #refresh the visibility of items according to the proxy filter (cf. checkboxes : populated, checked, published, accepted)
        self.trview_taxonref_refreshData()
        #ajust trview_taxonref column width
        total_width = self.trview_taxonref.viewport().width()
        self.trview_taxonref.setColumnWidth(0, int(total_width * 2 / 3))


    def trview_taxonref_refreshData(self, value = None):
        """GUI: Refresh trview_taxonref data (proxy) according to filter checkboxes"""
        #force the checkbox to be Checked or partially Checked
        if self.view.checkBox_children.checkState() == QtCore.Qt.Unchecked:
            self.view.checkBox_children.setCheckState(QtCore.Qt.PartiallyChecked) # trigger a recursive signal with validated state
            return
        #get the check states
        checked = self.view.checkBox_checked.checkState()
        published = self.view.checkBox_published.checkState()
        accepted = self.view.checkBox_accepted.checkState()
        children_only = self.view.checkBox_children.checkState() == 2
        self.proxy_model.show_checked_mode = checked
        self.proxy_model.show_published_mode = published
        self.proxy_model.show_accepted_mode = accepted
        self.proxy_model.children_only = children_only
        self.proxy_model.invalidateFilter()
        self.trview_taxonref.repaint()
        
        #reset the current index if not valid
        selected_index = self.trview_taxonref.currentIndex()
        if not selected_index.isValid():
            #self.trview_taxonref.setCurrentIndex(QtCore.QModelIndex())
            selected_index = self.trview_taxonref.model().index(0,0)

        #select if valid
        if selected_index.isValid():
            self.trview_taxonref.selectionModel().setCurrentIndex(
                    selected_index, QtCore.QItemSelectionModel.ClearAndSelect | QtCore.QItemSelectionModel.Rows)
            self.trview_taxonref.expand(selected_index)
        else:
            self.trview_hierarchy.model().clear()
            self.trview_properties.model().clear()
            self.trview_metadata.model().clear()
            self.trview_names.model().clear()
        self.refresh_ui_trview_hierarchy()



### MANAGE buttons   

    def on_button_reference_add_clicked(self):
        """GUI: Open the add reference window"""
        selecteditem = self.selectedItem
        if selecteditem is None:
            selecteditem = PNTaxa(1, 'Plantae',None,1, published=True, accepted=True) 
            #return            
        win = PNTaxa_add(selecteditem)
        win.apply_signal.connect(self.apply_edit_reference)
        win.show()

    def on_button_reference_edit_clicked(self):
        """GUI: Open the edit reference window"""
        if self.selectedItem is None:
            return
        win = PNTaxa_edit(self.selectedItem)
        win.apply_signal.connect(self.apply_edit_reference)
        win.show()

    def on_button_reference_remove_clicked(self):
        """GUI: Propose to delete a reference"""
        if self.selectedItem is None:
            return
        # message to be display first (question, Yes or No)
        msg = f"""Are you sure you want to delete \"{self.selectedItem.taxonref}\"?
        The children and all associated names will be permanently deleted"""
        result = MessageBox().question_msgbox("Delete a taxon", msg, True)
        if not result :
            return

        #delete is confirmed
        ls_todelete = db_taxa().db_delete_reference(self.selectedItem.id_taxonref)
        if ls_todelete: #not result.lastError().isValid():
            #refresh the model and combo_taxa
            try:
                #disconnect signal to avoid multiple events (except error if not yet connected)
                self.trview_taxonref.selectionModel().selectionChanged.disconnect()
            except Exception:
                pass
            # Remove the selected taxa and childs in model and combo_taxa
            for idtaxonref in ls_todelete:
                # remove the item from the model
                self.proxy_model.sourceModel().removeItem(idtaxonref)
                self.combo_taxa_deletedItem(idtaxonref)
            #select the current item
            index = self.trview_taxonref.currentIndex()
            if not index.isValid():
                index = self.proxy_model.index(0,0)
            self.trview_taxonref.setCurrentIndex(QtCore.QModelIndex())
            self.trview_taxonref.selectionModel().selectionChanged.connect(self.on_trview_taxonref_clicked)
            self.trview_taxonref.selectionModel().setCurrentIndex(index, QtCore.QItemSelectionModel.ClearAndSelect | QtCore.QItemSelectionModel.Rows)

    def on_button_reference_merge_clicked(self):
        """GUI: When clicked, propose to merge two taxa names from similar ranks"""
        # get the selectedItem
        try:
            selecteditem = self.selectedItem
            win = PNTaxa_merge(selecteditem)
            win.show()
            #refresh the trview_taxonref (win.main_tableView)
            if win.updated:
                idtaxonref = win.selected_idtaxonref
                category = win.selected_category
                from_idtaxonref = selecteditem.idtaxonref
                if idtaxonref == from_idtaxonref:
                    return
                # execute the merge into the database
                if db_taxa().db_merge_reference(from_idtaxonref, idtaxonref, category):
                    #reset the id of PN_trview_names to force refresh (toolbox trigger by self.trview_hierarchy)
                    self.trview_names.id = 0
                    self.trview_metadata.id = 0
                    idrank = selecteditem.id_rank
                    # deleted the input taxa
                    self.proxy_model.sourceModel().removeItem(from_idtaxonref)
                    #refresh the tlview_taxonref
                    if idrank >= self.selectedIdrank:
                        self.trview_taxonref_setData()
                        #self.trview_taxonref_refresh([idtaxonref])
                    
                    #get the selecteditem from the trview_taxonref.model
                    selecteditem = self.trview_taxonref_selectedItem #()
                    #if not found, create a new PNTaxa_with_Score
                    if selecteditem is None:
                        selecteditem = PNTaxa_with_Score(idtaxonref) #, False, False)
                    #set and select the merged item in the trview_hierarchy
                    if selecteditem:
                #ensure to see the idtaxonref, by switching the idrank temporarily
                        save_idrank = selecteditem.id_rank
                        selecteditem.id_rank = idrank
                        self.trview_hierarchy.setdata (selecteditem, idtaxonref)
                        selecteditem.id_rank = save_idrank
                else:
                    msg = db_postgres().postgres_error()
                    MessageBox().information_msgbox("Error", msg, True)
        except Exception:
            return

    def on_button_properties_cancel_clicked(self):
        """GUI: When clicked, propose to restore properties from the database"""
        msg = "Are you sure you want to undo all changes and restore from the database ?"
        result = MessageBox().question_msgbox("Cancel properties", msg)
        if not result:
            return
        #cancel is confirmed
        self.trview_properties.refresh()

    def on_button_filter_reset_clicked(self):
        """GUI: Reset the filter with null values and load no-filtered data"""
        self.view.search_taxon =""
        self.trview_filter_load()
        self.trview_taxonref_setData()
        
    def on_button_metadata_clicked(self):
        """GUI: Start metadata worker (Qthread) to search metadata from registred API and fill the trview_metadata"""
        # get the selectedItem
        if self.selectedItem is None:
            return
        self.view.button_metadata_refresh.setEnabled(False)
        if self.metadata_worker.status == 1:
            self.metadata_worker.kill()
            while self.metadata_worker.isRunning():                
                time.sleep(0.5)
        #add properties to count score
        self.selectedItem.taxaname_score = 0
        self.selectedItem.authors_score = 0

        self.view.label_time = str(time.strftime("%Y-%m-%d %H:%M:%S"))
        self.trview_metadata.dict_db_properties.clear()
        self.trview_metadata.setData({})
        self.metadata_worker.PNTaxa_model = self.selectedItem
        self.metadata_worker.start()
        self.trview_taxonref.repaint()


    def on_button_synonym_add_clicked(self):
        """GUI: Open the add synonym window"""
        # get the selectedItem
        if self.selectedItem is None:
            return
        if self.trview_names.currentIndex().parent().isValid():
            category = self.trview_names.currentIndex().parent().data()
        else:
            category = self.trview_names.currentIndex().data()
        new_synonym = PNSynonym(None, self.selectedItem.taxonref, self.selectedItem.idtaxonref, category)
        class_newname = PNSynonym_edit(new_synonym)
        class_newname.add_signal.connect(self.apply_add_synonym)
        class_newname.show()

    def on_button_synonym_edit_clicked(self):
        """GUI: Open the edit synonym window"""
        # get the selectedItem
        if self.selectedItem is None:
            return
        _syno = self.trview_names.currentIndex().data()
        category = self.trview_names.currentIndex().parent().data()
        if not _syno or not category:
            return
        edit_synonym = PNSynonym(_syno, self.selectedItem.taxonref, self.selectedItem.idtaxonref,category)
        #edit_synonym.id_synonym = 1
        class_newname = PNSynonym_edit(edit_synonym)
        class_newname.edit_signal.connect(self.apply_edit_synonym)
        class_newname.show()

    def on_button_synonym_remove_clicked(self):
        """GUI: Propose to delete a synonym and refresh the list of names"""
    #delete a synonym from the selected taxon
        if self.selectedItem is None:
            return
        if not self.trview_names.currentIndex().parent().isValid():
            return
        _currentsynonym = self.trview_names.currentIndex().data()
        if _currentsynonym is None:
            return

        # message to be display first (question, Yes or No)
        msg = f"Are you sure to permanently delete this name {_currentsynonym}?"
        result = MessageBox().question_msgbox("Delete a synonym", msg)
        if not result:
            return
        
        #delete into the database
        if db_taxa().db_delete_synonym(_currentsynonym):
            self.trview_names_setData()
        else:
            msg = db_postgres().postgres_error()
            MessageBox().information_msgbox("Error", msg, True)
        #refresh the ui buttons associated to trview_names
        self.refresh_ui_buttons_names()


    def apply_add_synonym(self, id_taxonref, new_synonym, new_category):
        """GUI: Add the new synonym and refresh the list of names"""
        if db_taxa().db_add_synonym(id_taxonref, new_synonym, new_category):
            #self.window.sender().Qline_name.setText('')
            #self.window.sender().myPNSynonym.category = new_category
            self.window.sender().myPNSynonym.synonym = ''
            self.window.sender().refresh()
            self.trview_names_setData()
        else:
            msg = db_postgres().postgres_error()
            MessageBox().information_msgbox("Error", msg, True)
        
    def apply_edit_synonym(self, synonym, new_synonym, new_category):
        """GUI: Update the modified version of the synonym and refresh the list of names"""
        if db_taxa().db_edit_synonym(synonym, new_synonym, new_category):
            self.window.sender().myPNSynonym.synonym = new_synonym
            self.window.sender().myPNSynonym.category = new_category
            self.window.sender().refresh()
            self.trview_names_setData()
        else:
            msg = db_postgres().postgres_error()
            MessageBox().information_msgbox("Error", msg, True)


   
    def apply_edit_reference(self, ls_dict_tosave):
        """GUI: Updating/Adding database references from a list of taxa-dictionaries (dict_taxa)"""
        #internal function for saving one taxon in the database
        # """ 
        #     common function for update (add_name and edit_name) when apply
        #     Save a taxon in the database from a list of dictionnaries:   
        #     if parentname is not present, it will update the taxon with id_parent = (searching the id_parent, in the dbase taxaname = parentname)
        #     dict_tosave = {"id_taxonref":integer, "basename":text, "authors":text, "parentname":text, "published":boolean, "accepted":boolean, "id_rank" :integer}
        #     if idparent is present, it will update the taxon with the id_parent (integer)
        #     dict_tosave = {"id_taxonref":integer, "basename":text, "authors":text, "id_parent":integer, "published":boolean, "accepted":boolean, "id_rank" :integer}
        # """
        #####main part of the function
        if not isinstance(ls_dict_tosave, list):
            ls_dict_tosave = [ls_dict_tosave]   
        ls_item_updated = []
        #save any dict from the list
        for dict_tosave in ls_dict_tosave:
            idtaxonref_torefresh  = db_taxa().db_save_dict_taxa(dict_tosave)
            _idrank = dict_tosave.get("id_rank", 0)
            if idtaxonref_torefresh :
                ls_item_updated.append(idtaxonref_torefresh)
                #ensure to update the id_taxonref in the dict_tosave
                dict_tosave["id_taxonref"] = idtaxonref_torefresh
            else:
                msg = db_postgres().postgres_error()
                MessageBox().information_msgbox("Error", msg, True)
        
        #refresh UI if updated (tlview_taxonref and trview_hierarchy)
        #if ls_item_updated:
            #reset the id of PN_trview_names to force refresh (toolbox trigger by self.trview_hierarchy)
            # self.trview_names.id = 0
            # self.trview_metadata.id = 0
            #idrank = max(obj["id_rank"] for obj in ls_dict_tosave)
            #refresh the tlview_taxonref if rank is include into the view (grouped_idrank or higher)
            #if idrank >= self.get_idrankGroup():
        if not ls_item_updated:
            return

        selecteditem = self.window.sender().PNTaxa
        idtaxonref = selecteditem.idtaxonref 
        ls_hierarchy = selecteditem.list_hierarchy

        #refresh data in trview_taxonref
        self.trview_taxonref_setData()
        #print (ls_dict_tosave[0].get("id_taxonref", self.window.sender().PNTaxa.idtaxonref))

        #self.trview_taxonref_refresh(ls_dict_tosave)
        #get the selecteditem from the trview_taxonref.model
        # selecteditem = None #self.trview_taxonref_selectedItem #()
        
        #idtaxonref = ls_dict_tosave[0].get("id_taxonref", self.window.sender().PNTaxa.idtaxonref)

        # idtaxonref = self.window.sender().PNTaxa.idtaxonref

        # #if no selection, create a new PNTaxa_with_Score to be sure to get hierarchy of item
        # #if selecteditem is None:
        #     #selecteditem = PNTaxa_with_Score(idtaxonref)
        # selecteditem = self.trview_hierarchy.selecteditem()
        # idtaxonref = selecteditem.idtaxonref

        #get the hierarchy of the selecteditem
        for item in ls_hierarchy:
            if item["id_rank"] == self.selectedIdrank:
                self.trview_taxonref_selectedItem = item["id_taxonref"]
                selecteditem = self.trview_taxonref_selectedItem
                break


        #set and select the item in the trview_hierarchy, with idtaxonref as selected item
        if selecteditem:
            #ensure to see the idtaxonref
            self.trview_hierarchy.setdata (selecteditem, idtaxonref)
        #efresh the sender PNTaxa_edit or PNTaxa_add
        self.window.sender().PNTaxa = self.selectedItem
        self.window.sender().refresh()



#refresh ui
    def refresh_ui_trview_taxonref(self, enabled: bool):
        """GUI: Refresh access to widgets linked to trview_taxonref"""
        self.view.button_showFilter.setEnabled(enabled)
        self.view.button_rankgroup.setEnabled(enabled)
        self.view.combo_taxa.setEnabled(enabled)
        self.view.checkBox_published.setEnabled(enabled)
        self.view.checkBox_accepted.setEnabled(enabled)
        self.view.checkBox_checked.setEnabled(enabled)
        self.view.checkBox_children.setEnabled(enabled)
        self.view.button_reference_add.setEnabled(enabled)

    def refresh_ui_trview_hierarchy(self):
        """GUI: Refresh access to widgets linked to trview_hierarchy"""
    # refresh buttons, labels in the main UI (mainwindow)
        self.view.button_synonym_add.setEnabled(False)
        self.view.button_metadata_refresh.setEnabled(False)
        self.view.button_reference_edit.setEnabled(False)
        self.view.button_reference_merge.setEnabled(False)
        self.view.button_reference_remove.setEnabled(False)
        self.view.label_count = "< No Selection >"
        
        self.refresh_ui_label_count()
        self.refresh_ui_label_taxa()
        self.refresh_ui_buttons_names()
        # check if a taxon is selected
        selected_taxa = self.selectedItem
        if selected_taxa is None:
            self.trview_properties.setData()
            self.trview_metadata.setData()
            self.trview_names.setData()
            return
        elif not hasattr(selected_taxa, 'idtaxonref'):
            return
        elif selected_taxa.idtaxonref == 0:
            return
        
        #if a taxon is selected....
        self.view.button_synonym_add.setEnabled(True)
        self.view.button_metadata_refresh.setEnabled(True)
        #self.view.button_rankgroup.setEnabled(True)

        # buttons references visibility
        #self.view.button_reference_add.setEnabled(True)
        value = selected_taxa.id_rank >2
        self.view.button_reference_edit.setEnabled(value)
        self.view.button_reference_merge.setEnabled(value)
        self.view.button_reference_remove.setEnabled(value)

    def refresh_ui_buttons_names(self):
        """GUI: Refresh access to buttons linked to self.trview_names"""
    # refresh buttons names enabled state according to trview_name.selectedItem
        value = False
        try:
            if self.trview_names.currentIndex().parent().isValid():
                value = self.trview_names.currentIndex().parent().data() != 'Autonyms'
        except Exception:
            value = False
        self.view.button_synonym_edit.setEnabled(value)
        self.view.button_synonym_remove.setEnabled(value)

    def refresh_ui_label_count(self):
        """GUI: Refresh the count of taxa and groups in the main UI (mainwindow)"""
    # Refresh taxa and group count with the model values
        count_taxa = self.proxy_model.childCount()
        count_parent = self.proxy_model.rowCount()
        #set the count parent, taxa
        group_text = self.view.button_rank_text
        _suffix = 'taxon'
        if count_taxa > 1:
            _suffix = 'taxa'
        msg = f" {count_taxa} {_suffix}, {count_parent} {group_text}(s)"
        self.view.label_count = msg
    
    def refresh_ui_label_taxa(self):
        """GUI: Refresh the count of subtaxa in the main UI (mainwindow)"""
    #Refresh the taxa label with the current trview_taxonref selected item
        #self.view.set_taxa_label("< No Selection >")
        self.view.label_taxa = "< No Selection >"
        selecteditem = self.trview_taxonref_selectedItem #()
        if selecteditem is None:
            return
        child_count = self.proxy_model.rowCount(self.trview_taxonref.currentIndex())
        _suffix = 'taxon'
        if child_count > 1:
            _suffix = 'taxa'
        #self.view.set_taxa_label(f"{selecteditem.taxonref} ({child_count} {_suffix})")
        self.view.label_taxa = f"{selecteditem.taxonref} ({child_count} {_suffix})"
    
    def close(self):
        """GUI: Close the main UI (mainwindow)"""
        self.window.close()

    def show(self):
        """GUI: Open the main UI (mainwindow)"""
        self.on_menu_theme_clicked (self.config_manager.theme)
        self.window.show()
        self.database_open()

def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    controller = MainWindowController(window)
    controller.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
    

