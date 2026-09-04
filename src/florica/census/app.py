import os
import sys
import json
from pathlib import Path
from unittest import result
from PyQt5 import QtCore, QtGui, QtWidgets

from florica.core.widgets import PN_JsonQTreeView, _EditProperties_Delegate, PostgresConfigDialog, load_ui_from_resources, MessageBox, ConfigManager, setup_theme_menu, set_theme
from florica.core import database, resources

class ColumnSelector(QtCore.QObject):

    columnsChanged = QtCore.pyqtSignal(list)

    def __init__(self, table_view, columns, display_columns, excluded_columns = [], parent=None):
        super().__init__(parent)

        self.table_view = table_view
        self.columns = columns
        self.display_columns = display_columns
        self.excluded_columns = excluded_columns

        header = table_view.horizontalHeader()
        header.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        header.customContextMenuRequested.connect(self.show_menu)

    def show_menu(self, pos):
        menu = QtWidgets.QMenu(self.table_view)

        for name in self.columns:
            if name in self.excluded_columns:
                continue

            action = menu.addAction(name)
            action.setCheckable(True)
            action.setChecked(name in self.display_columns)

            action.toggled.connect(
                lambda checked, name=name: self.toggle(name, checked)
            )

        menu.exec_(self.table_view.horizontalHeader().viewport().mapToGlobal(pos))

    def toggle(self, name, display):
        if display:
            if name not in self.display_columns:
                self.display_columns.append(name)
        else:
            if name in self.display_columns:
                self.display_columns.remove(name)

        self.columnsChanged.emit(self.display_columns)


class TreesFilterProxy(QtCore.QSortFilterProxyModel):
    """
    This class represents a proxy model for filtering trees based on boolean values.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.boolean_filters = {}

    def filterAcceptsRow(self, source_row, source_parent):
        index = self.sourceModel().index(
            source_row,
            0,
            source_parent
        )
        tree = index.data(QtCore.Qt.UserRole)
        if not tree:
            return True
        for field, wanted in self.boolean_filters.items():
            if wanted is None:
                continue
            if tree.get(field) != wanted:
                return False
        return True



##The MainWindow load the ui interface to navigate and edit taxaname###
class MainWindow(QtWidgets.QMainWindow):
    """
    This class represents the main window of the application and is responsible for managing the user interface. 
    Provide properties to manage the UI elements.
    """

    #toolbox_click = QtCore.pyqtSignal(int)
    def __init__(self):
        super().__init__()
        # load the GUI
        self.window = load_ui_from_resources("plots.ui")
        self._ui_enabled = True
        self.window.frame_history_slider.setVisible(False)
        self.button_themes = self.window.button_themes
        self.window.statusBar().addPermanentWidget(self.button_themes)
        

    # # setting the widgets links to ui
    #     self.trview_taxonref = self.window.main_treeView
    #     self.button_metadata_refresh = self.window.button_metadata_refresh
        self.buttonbox_filter = self.window.buttonBox_filter
        self.buttonbox_filter_apply = self.window.buttonBox_filter.button(QtWidgets.QDialogButtonBox.Apply)
        self.buttonbox_filter_reset = self.window.buttonBox_filter.button(QtWidgets.QDialogButtonBox.Reset)

    #     self.button_properties = self.window.buttonBox_identity
    #     self.button_properties_apply = self.button_properties.button(QtWidgets.QDialogButtonBox.Apply)
    #     self.button_properties_cancel = self.button_properties.button(QtWidgets.QDialogButtonBox.Cancel)
    #     self.button_reference_add = self.window.button_reference_add
    #     self.button_reference_edit = self.window.button_reference_edit
    #     self.button_reference_remove = self.window.button_reference_remove
    #     self.button_reference_merge = self.window.button_reference_merge
    #     self.button_synonym_add = self.window.button_synonym_add
    #     self.button_synonym_edit = self.window.button_synonym_edit
    #     self.button_synonym_remove = self.window.button_synonym_remove
    #     self.button_rankgroup = self.window.button_rankGroup
    #     self.button_themes = self.window.button_themes
        self.button_showFilter = self.window.button_showFilter

    #     self.checkBox_published = self.window.checkBox_published
    #     self.checkBox_accepted = self.window.checkBox_accepted
    #     self.checkBox_children = self.window.checkBox_withtaxa
    #     self.checkBox_checked = self.window.checkBox_checked
        self.searchplot = self.window.lineEdit_searchplot
    #     self.toolBox = self.window.toolBox
        self.combo_plot = self.window.comboBox_types

    # #setting the filter checkboxes to partially checked
    #     self.checkBox_published.setCheckState(QtCore.Qt.PartiallyChecked)
    #     self.checkBox_accepted.setCheckState(QtCore.Qt.PartiallyChecked)
    #     self.checkBox_children.setCheckState(QtCore.Qt.PartiallyChecked)
    #     self.checkBox_checked.setCheckState(QtCore.Qt.PartiallyChecked)

    # #set the buttons icons
        self.buttonbox_filter_apply.setIcon (QtGui.QIcon(":src/florica/resources/icons/ok.png"))
        self.buttonbox_filter_reset.setIcon (QtGui.QIcon(":src/florica/resources/icons/refresh.png"))
    #     self.button_properties_apply.setIcon (QtGui.QIcon(":src/florica/resources/icons/ok.png"))
    #     self.button_properties_cancel.setIcon (QtGui.QIcon(":src/florica/resources/icons/nok.png"))

    # #set the toolbox icon style
    #     index = self.toolBox.currentIndex()
    #     self._on_toolbox_click(index)
    
    # #add two labels to displayed msg in the statusbar
    #     self.selected_rank_label = QtWidgets.QLabel()
    #     self.selected_taxa_label = QtWidgets.QLabel()
    #     self.window.statusbar.addWidget(self.selected_rank_label)
    #     self.window.statusbar.addWidget(self.selected_taxa_label)
    #     self.window.statusBar().addPermanentWidget(self.button_themes)
    #     self.toolBox.currentChanged.connect(self._on_toolbox_click)

    # def _on_toolbox_click(self, index):
    #     #set the icons to the toolbox and emit a signal
    #     self.toolBox.setItemIcon(index, QtGui.QIcon(":src/florica/resources/icons/arrow2.png"))
    #     for i in range(3):
    #         if i != index:
    #             self.toolBox.setItemIcon(i, QtGui.QIcon(":src/florica/resources/icons/arrow1.png"))
    #     self.toolbox_click.emit(index)
    
    # @property
    # def ui_enabled(self) -> bool:
    #     """Get or set the enabled state of the ui (buttons, combo, checkbox)"""
    #     return self._ui_enabled
    # @ui_enabled.setter
    # def ui_enabled(self, enabled: bool):
    #     self._ui_enabled = enabled
    #     #set the enabled state of the ui
    #     self.button_synonym_add.setEnabled(enabled)
    #     self.button_synonym_edit.setEnabled(enabled)
    #     self.button_synonym_remove.setEnabled(enabled)
    #     self.button_reference_merge.setEnabled(enabled)
    #     self.button_reference_edit.setEnabled(enabled)
    #     self.button_reference_remove.setEnabled(enabled)
    #     self.button_metadata_refresh.setEnabled(enabled)
    #     self.button_reference_add.setEnabled(enabled)
    #     #major buttons
    #     self.button_showFilter.setEnabled(enabled)
    #     self.button_rankgroup.setEnabled(enabled)
    #     self.combo_taxa.setEnabled(enabled)
    #     self.checkBox_published.setEnabled(enabled)
    #     self.checkBox_accepted.setEnabled(enabled)
    #     self.checkBox_checked.setEnabled(enabled)
    #     self.checkBox_children.setEnabled(enabled)

    @property
    def buton_theme_text(self) -> str:
        """Get or set the text for the button themes"""
        return self.window.button_themes.text()
    @buton_theme_text.setter
    def buton_theme_text(self, text: str):
        self.window.button_themes.setText(text or "Default Style")

    # @property
    # def button_rank_text(self) -> str:
    #     """Get or set the text for the rank button"""
    #     return self.button_rankgroup.text()
    # @button_rank_text.setter
    # def button_rank_text(self, text: str):
    #     self.button_rankgroup.setText(text) 

    @property
    def button_filter_visible(self) -> bool:
        """Get or set the visibility of the filter Frame"""
        return self.window.frame_filter.isVisible()
    @button_filter_visible.setter
    def button_filter_visible(self, visible: bool):
        self.window.frame_filter.setVisible(visible)

    # @property
    # def label_rank(self) -> str:
    #     """Get or set the text for the label_rank"""
    #     return self.selected_rank_label.text()
    # @label_rank.setter
    # def label_rank(self, text: str):
    #     self.selected_rank_label.setText(text)

    # @property
    # def label_taxa(self) -> str:
    #     """Get or set the text for the label_taxa"""
    #     return self.selected_taxa_label.text()
    # @label_taxa.setter
    # def label_taxa(self, text: str):
    #     self.selected_taxa_label.setText(text)

    # @property
    # def label_count (self) -> str:
    #     """Get or set the text for the label_count"""
    #     return self.window.label_count.text()
    # @label_count.setter
    # def label_count (self, text: str):
    #     self.window.label_count.setText(text)

    # @property
    # def label_time (self) -> str:
    #     """Get or set the text for the label_query_time"""
    #     return self.window.label_query_time.text()
    # @label_time.setter
    # def label_time (self, text: str):
    #     self.window.label_query_time.setText(text)

    @property
    def search_plot(self) -> str:
        """Get or set the text for the filter search_taxon"""
        return self.searchplot.text().strip()
    @search_plot.setter    
    def search_plot(self, text: str):
        self.searchplot.setText(text)



class MainWindowController:
    """
        The MainWindowController class is a controller for the main window of the application.
        Sets the view, window, connected status, db properties, authors delegate,
        config manager, and loads widgets from and to the view.
        It sets the filtering and sorting on the proxy model for trview_taxonref,
        Creates the metadata worker (Qthread) and sets the slots signals.
    """    
#the main controller of the application
    def __init__(self, view):
        self.view = view
        self.window = self.view.window
        self.connected = False
        self.db_properties = None
        self.view.button_filter_visible = False
        self.checkbox_trees_filter_enabled = False
        self.tree_observations = []

        #load the config file
        BASE_DIR = Path(__file__).resolve().parents[1]
        config_file = os.path.join(BASE_DIR, "config.ini")

        #config_file = functions.resource_path("config.ini")
        self.config_manager = ConfigManager(config_file)

        #load widgets from the view
        #self.trview_taxonref = view.trview_taxonref
        
        #load widgets to the view
        self.dbwidget = database.DatabaseConnection()
        self.window.statusBar().addPermanentWidget(self.dbwidget)

           #load themes menu
        # setup_theme_menu(
        #     self.view.button_themes,
        #     self.on_menu_theme_clicked
        # )
        setup_theme_menu (self.view.button_themes, self.config_manager)
        # button_themes_menu = QtWidgets.QMenu()
        # #menu_items = ["Adaptic", "Combinear", "Diffnes", "Geoo", "Lightstyle", "Obit"]
        # menu_items = get_qss_themes()
        # for item in menu_items:
        #     action = QtWidgets.QAction(item, self.view)
        #     action.triggered.connect(lambda checked, item=item: self.on_menu_theme_clicked(item))
        #     button_themes_menu.addAction(action)
        # self.view.button_themes.setMenu(button_themes_menu)


        # self.trview_properties =  PN_JsonQTreeView ()
        # layout = self.window.toolBox.widget(2).layout()
        # layout.insertWidget(0,self.trview_properties) 

        # self.trview_metadata = PN_JsonQTreeView ()
        # layout = self.window.toolBox.widget(1).layout()
        # layout.insertWidget(0,self.trview_metadata)

        # self.trview_names = PN_JsonQTreeView ()
        # layout = self.window.toolBox.widget(0).layout()
        # layout.insertWidget(0,self.trview_names)

        # self.trview_tree = PN_JsonQTreeView ()
        # tab = self.window.tabWidget_tree.widget(1)
        # layout = tab.layout()
        # # if layout is None:
        # #     layout = QtWidgets.QVBoxLayout(tab)
        # layout.insertWidget(0, self.trview_tree)

        self.trview_history = PN_JsonQTreeView ()
        layout = self.window.tabWidget_tree.widget(2).layout()
        layout.insertWidget(1, self.trview_history)


        # self.view.buttonbox_filter_apply.setEnabled(False)
        # self.view.buttonbox_filter_reset.setEnabled(False)

        


        # self.trview_history = PN_JsonQTreeView ()
        # # self.trview_history.setFrameShape(QtWidgets.QFrame.Box)
        # # self.trview_history.setFrameShadow(QtWidgets.QFrame.Plain)
        # # self.trview_history.setLineWidth(1)

        # # self.trview_history.setAlternatingRowColors(True)
        # #tab = self.window.tabWidget_tree.widget(1)
        # frame = self.window.frame_tree
        # layout = frame.layout()
        # if layout is None:
        #     layout = QtWidgets.QVBoxLayout(frame)
        # layout.addWidget(self.trview_history)



        


        
        # self.combo_taxa = view.combo_taxa

         #set filtering and sorting on the proxymodel for trview_taxonref
#         self.trview_taxonref.setSortingEnabled(True)
#         self.trview_taxonref.header().setSortIndicator(0, QtCore.Qt.AscendingOrder)
#         self.proxy_model = _TaxonomyProxyModel()
#         self.proxy_model.setSourceModel(PNTaxa_treeModel())
#         self.proxy_model.setDynamicSortFilter(True)
#         self.proxy_model.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)
#         self.trview_taxonref.setModel(self.proxy_model)
        





        
#         #create the metadata worker (Qthread)
#         self.metadata_worker = PNTaxa_searchAPI(view)

#         self.trview_metadata.setItemDelegate(self.authors_delegate)

#     #setting the slots signals
#         #signals from menus clicked (theme and rank group)
#         self.view.toolbox_click.connect(self.on_toolbox_clicked)
#         #signals from buttons
        self.view.button_showFilter.toggled.connect(self.on_button_filter_clicked)  
#         self.view.button_synonym_add.clicked.connect(self.on_button_synonym_add_clicked)
#         self.view.button_synonym_edit.clicked.connect(self.on_button_synonym_edit_clicked)
#         self.view.button_synonym_remove.clicked.connect(self.on_button_synonym_remove_clicked)
#         self.view.button_reference_add.clicked.connect(self.on_button_reference_add_clicked)   
#         self.view.button_reference_edit.clicked.connect(self.on_button_reference_edit_clicked)
#         self.view.button_reference_remove.clicked.connect(self.on_button_reference_remove_clicked)
#         self.view.button_reference_merge.clicked.connect(self.on_button_reference_merge_clicked)
#         self.view.button_metadata_refresh.clicked.connect (self.on_button_metadata_clicked)
#         self.view.button_properties_apply.clicked.connect(self.apply_edit_properties)
#         self.view.button_properties_cancel.clicked.connect(self.on_button_properties_cancel_clicked)
#         #signals from searchTaxon enter
        self.view.searchplot.returnPressed.connect(self.load_plots)
#         #signals from checkboxes
#         self.view.checkBox_published.stateChanged.connect(self.trview_taxonref_refreshData)
#         self.view.checkBox_accepted.stateChanged.connect(self.trview_taxonref_refreshData)
#         self.view.checkBox_children.stateChanged.connect(self.trview_taxonref_refreshData)
#         self.view.checkBox_checked.stateChanged.connect(self.trview_taxonref_refreshData)
#         #signals from trviews    
#         self.trview_taxonref.selectionModel().selectionChanged.connect(self.on_trview_taxonref_clicked)
#         self.trview_taxonref.doubleClicked.connect(self.on_trview_taxonref_dblclicked)
#         self.trview_hierarchy.selectionModel().selectionChanged.connect(self.on_trview_hierarchy_clicked)
#         self.trview_hierarchy.doubleClicked.connect(self.on_trview_hierarchy_dblclicked)
#         self.trview_names.selectionModel().selectionChanged.connect(self.refresh_ui_trview_hierarchy)
        #self.trview_filter.changed_signal.connect(self._refresh_enabled_buttons_filter)
        self.model_plots = QtGui.QStandardItemModel()
        self.window.tableView_plots.setModel(self.model_plots)

#generate a proxy model for trees
        self.model_trees = QtGui.QStandardItemModel()
        self.proxy_trees = TreesFilterProxy(self.view)
        self.proxy_trees.setSourceModel(self.model_trees)
        self.window.tableView_trees.setModel(self.proxy_trees)

#open database
        self.database_open()

#insert dynamic filter and tree properties
        #insert and load the self.trview_filter in editmode with the dictionnary
        dict_db_properties = database.dbplot().db_dict_plot_properties
        self.trview_filter = PN_JsonQTreeView (dict_fieldDefs = dict_db_properties)
        layout = self.window.frame_filter.layout()
        layout.insertWidget(1,self.trview_filter)
        #load the dictionnary of self.trview_filter with null values
        dict_properties = {}
        for _key, _value in dict_db_properties.items():
            dict_properties[_key] = {}.fromkeys(_value,'')            
        self.trview_filter.setData(dict_properties)

        # dict_properties2 ={}
        # for _key, _value in database.dbplot().db_dic_plots.items():
        #     dict_properties2[_key] = ''
        # dict_properties = dict_properties2 |dict_properties
            
        dict_db_properties = database.dbplot().db_dic_plots
        self.trview_plot = PN_JsonQTreeView (dict_fieldDefs = dict_db_properties)
        layout = self.window.tabWidget_tree.widget(0).layout()
        layout.insertWidget(1,self.trview_plot)


        #load the self.trview_tree in editmode with the dictionnary
        dict_db_properties = database.dbplot().db_dic_traits
        self.trview_tree = PN_JsonQTreeView (dict_fieldDefs = dict_db_properties)
        layout = self.window.tabWidget_tree.widget(1).layout()
        layout.insertWidget(0, self.trview_tree)


    #load the checkbox filter according to the db_dic_traits
        dict_fields = database.dbplot().db_dic_traits
        _style = """
            QCheckBox::indicator:checked {
                background-color: rgb(0, 255, 0);
                border: 1px solid darkgreen;
            }
            QCheckBox::indicator:unchecked {
                background-color: rgb(255, 0, 0);
                border: 1px solid darkred;
            }
            QCheckBox::indicator:indeterminate {
                background-color: white;
                border: 1px solid #555;
            }
        """  
        position = self.window.tree_filter_Hlayout.count()-1      
        for field, value in dict_fields.items():
            if value["type"] == "boolean":
                checkbox = QtWidgets.QCheckBox(field.capitalize(), self.view)
                checkbox.setStyleSheet(_style)
                checkbox.setProperty("field_name", field)
                checkbox.setTristate(True)
                checkbox.setCheckState(QtCore.Qt.PartiallyChecked)
                checkbox.stateChanged.connect(lambda state, name=field:
                    self.set_boolean_filter(name, state)
                )
                self.window.tree_filter_Hlayout.insertWidget(position, checkbox)
                position += 1           

    #load the tableview_tree_column_editor
        self.tableView_trees_column_selector = ColumnSelector(
            self.window.tableView_trees,
            list(database.dbplot().db_dic_traits.keys()),
            ["identifier", "taxaname", "date_obs"],
            ["identifier", "taxaname", "year", "month", "day", "id_tree"],
            self.window.tableView_trees
        )
        self.tableView_trees_column_selector.columnsChanged.connect(self._on_column_trees_changed)

  
#connect signals
        self.view.combo_plot.currentIndexChanged.connect(self._on_combo_plot_clicked)
        self.window.tableView_plots.selectionModel().selectionChanged.connect(self._on_tableview_plots_changed)
        self.window.tableView_trees.selectionModel().selectionChanged.connect(self._on_tableview_trees_changed)
        self.window.slider_history.valueChanged.connect(self._on_slider_history_valueChanged)

        self.dbwidget.clicked.connect(self.on_status_clicked)

        self.view.buttonbox_filter_apply.clicked.connect(self.load_plots)
        self.view.buttonbox_filter_reset.clicked.connect(self._on_button_filter_reset_clicked)

        self.load_plots()

    @property
    def selected_treesFilter(self):
        """
        GUI: Returns a dictionary of filters (db_tree_filter) from the UI
        """
        dict_filter = database.dbplot().db_dic_tree_filter

        #get the list of selected plots from the tableView_plots
        selection_model = self.window.tableView_plots.selectionModel()
        id_plots = [
            json.loads(index.data(QtCore.Qt.UserRole))["id_plot"]
            for index in selection_model.selectedRows(0)
        ]
        dict_filter["id_plots"] = id_plots
        #dict_filter["properties"] = {'phenology': {'fleur': 'True'}}

        # print (dict_filter)
        return dict_filter

    
    @property
    def selected_plotFilter(self):
        """
        GUI: Returns a dictionary of filters (db_plot_filter) from the UI (combo_plot)
        """
        dict_filter = database.dbplot().db_dic_plot_filter

        #1) filter on plot name
        if len(self.view.search_plot) > 0:
            dict_filter["search_plot"] = self.view.search_plot

        #2) filter on plot type
        combo_plot_index = self.view.combo_plot.currentIndex()
        if combo_plot_index > 0:
            dict_filter["type_plot"] = self.view.combo_plot.itemText(combo_plot_index)

        #3) filter on properties        
        properties_filter = self.trview_filter.build_properties_filter()
        if properties_filter:
            dict_filter["properties"] = properties_filter
        return dict_filter


    def set_boolean_filter(self, name, state):
        """
            GUI: set the boolean filter
        """
        if state == QtCore.Qt.Checked:
            value = True
        elif state == QtCore.Qt.Unchecked:
            value = False
        else:
            value = None
        self.proxy_trees.boolean_filters[name] = value
        self.proxy_trees.invalidateFilter()


    def _on_button_filter_reset_clicked(self):
        """GUI: Reset the filter with null values and load no-filtered data"""
        self.view.search_plot =""
        self.trview_filter.refresh()
        self.load_plots()

    def on_button_filter_clicked(self, state: bool):
        """GUI : hide/show filter Frame according to the state of the button_showFilter"""
        #self.view.set_filter_visible(state)
        self.view.button_filter_visible = state        

    def _on_combo_plot_clicked(self, state: bool):
        """GUI : hide/show filter Frame according to the state of the button_showFilter"""
        #self.view.set_filter_visible(state)
        self.load_plots()

    def _on_tableview_plots_changed(self, selected, deselected):
        """GUI : load the trees according to the selected plot"""
        #get the selected plot
        self.model_trees.clear()
        if selected:
            plot = json.loads(selected.indexes()[0].data(QtCore.Qt.UserRole)) #selected.indexes()[0].data(QtCore.Qt.UserRole)
            self.trview_plot.setData(plot)
            trees = database.dbplot().db_get_json_trees(self.selected_treesFilter) 
            self.tableView_trees_refresh(trees)


    def _on_tableview_trees_changed(self, selected, deselected):
        """GUI : load the trees and plot according to the selected tree"""
        #get the selected tree
        if selected:
            tree_data = selected.indexes()[0].data(QtCore.Qt.UserRole)
            
        #load the tree data into the trview_properties
            _observations,  history = database.dbplot().db_get_json_tree_properties(tree_data.get("id_tree"), tree_data.get("id_plot"))

        #get the plot data of the selected tree (searchinto th eplot selection)
            plot = {}
            plot_selection_model = self.window.tableView_plots.selectionModel()
            plot_selected_indexes = plot_selection_model.selectedRows(0)
            for _plots in plot_selected_indexes:
                if json.loads(_plots.data(QtCore.Qt.UserRole))["id_plot"] == tree_data.get("id_plot"):
                    plot =json.loads(_plots.data(QtCore.Qt.UserRole))
                    break
            #add the x, y coordinates of the tree in the plot
            plot["x"] = tree_data.get("x", '')
            plot["y"] = tree_data.get("y", '')
            #set the plot data in the trview_plot
            self.trview_plot.setData(plot)

        #create the self.tree_observations
            self.tree_observations = [tree_data]+_observations
        #and set the data from index = 0 (current)
            self.trview_tree_setData()
        #and set the history
            self.trview_history.setData(history)
        #manage the slider visibility and range
            self.window.frame_history_slider.setVisible(False)
            if len(self.tree_observations) > 1:
                self.window.frame_history_slider.setVisible(True)
                self.window.slider_history.setMinimum(0)
                self.window.slider_history.setMaximum(len(self.tree_observations)-1)
                self.window.slider_history.setValue(0)
                self.window.history_year_max.setText("Current") #str(self.tree_observations[0]["year"]))
                self.window.history_year_min.setText(str(self.tree_observations[-1]["year"]))
        else:
            self.trview_tree.setData({})


    def _on_slider_history_valueChanged(self, value):
        """GUI : set the tree data according to the slider value"""
        self.trview_tree_setData(value)

    def trview_tree_setData(self, index = 0):
        """GUI : set the tree data according to the index in the self.tree_observations"""
        dict_obs = self.tree_observations[index]        
        field_trees = database.dbplot().db_dic_traits
        if index == 0:
            fields = {
                key: dict_obs.get(key, "")
                for key in field_trees
                if key in dict_obs and dict_obs[key]
            }
        else:
            fields = {
                key: dict_obs.get(key, "")
                for key in field_trees
            }
        #fill the trview_tree with the fields
        self.trview_tree.setData(fields)


    def load_plots(self, id_plot = None):
        self.model_plots.clear()
        self.model_trees.clear()
    #load the plots according to the plot filter
        dict_filter = self.selected_plotFilter
        nb_filter = sum(v is not None and k!="id_taxonref" for k, v in dict_filter.items())
        self.view.button_showFilter.setStyleSheet(
                "color: rgb(0, 55, 217);" if nb_filter else ""
        )
    #loads plots data from database
        ls_columns = ['plot', 'type', 'dimension']
        self.model_plots.setHorizontalHeaderLabels(ls_columns)
        data = database.dbplot().db_get_json_plots(dict_filter)
        for plot in data:
            row = []
            for col in ls_columns:
                item = QtGui.QStandardItem(str(plot.get(col, "")))
                row.append(item)
            row[0].setData(json.dumps(plot, ensure_ascii=False), 
                            role=QtCore.Qt.UserRole)
            row[0].setIcon(
            self.plot_type_icon(plot.get("type", "").lower())
            )
            self.model_plots.appendRow(row)
        #self.window.tableView_plots.setModel(model_plots)
        self.window.tableView_plots.resizeColumnsToContents()
        header = self.window.tableView_plots.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)

        if self.model_plots.rowCount() > 0:
            index = self.model_plots.index(0, 0)
            self.window.tableView_plots.setCurrentIndex(index)
            self.window.tableView_plots.selectRow(0)

    def plot_type_icon(self, plot_type, size=22):
        pixmap = QtGui.QPixmap(size, size)
        pixmap.fill(QtCore.Qt.transparent)

        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        painter.setPen(QtGui.QPen(QtGui.QColor("#555555"), 2))
        painter.setBrush(QtGui.QColor("#AAAAAA"))

        center = size // 2

        if plot_type == "point":
            painter.drawEllipse(6, 6, size-12, size-12)

        elif plot_type == "circle":
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawEllipse(3, 3, size-6, size-6)

        elif plot_type == "rectangle":
            painter.setBrush(QtCore.Qt.NoBrush)
            painter.drawRect(4, 4, size-8, size-8)

        elif plot_type == "transect":
            painter.drawLine(3, center, size-3, center)

        painter.end()

        return QtGui.QIcon(pixmap)

    def stems_icon(self, tree, size=24):
        _dead = tree.get("dead", None)
        _present = tree.get("present", None)
        _stems = tree.get("stems", None)

        pixmap = QtGui.QPixmap(size, size)
        pixmap.fill(QtCore.Qt.transparent)

        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        # color according to the tree status
        if _dead:
            color = "#D9534F"
        elif not _present:
            color = "#F0AD4E"
        else:
            color = "#5CB85C"


        # cercle
        painter.setBrush(QtGui.QColor(color))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawEllipse(0, 0, size, size)

        # nombre de tiges
        painter.setPen(QtGui.QColor("white"))
        font = painter.font()
        font.setBold(True)
        font.setPointSize(12)
        painter.setFont(font)
        if _stems:
            painter.drawText(
                pixmap.rect(),
                QtCore.Qt.AlignCenter,
                str(_stems)
            )

        painter.end()

        return QtGui.QIcon(pixmap)

    
    # def load_trees (self, id_plot = None):
    #     trees = database.dbplot().db_get_json_trees(self.selected_treesFilter) 
    #     self.tableView_trees_refresh(trees)

    def _on_column_trees_changed(self, columns):
        trees = []
        for row in range(self.model_trees.rowCount()):
            item = self.model_trees.item(row, 0)
            tree = item.data(QtCore.Qt.UserRole)
            if tree is not None:
                trees.append(tree)
        self.tableView_trees_refresh(trees)

    def tableView_trees_refresh(self, trees):
        ls_columns =  self.tableView_trees_column_selector.display_columns
        self.model_trees.clear()
        self.model_trees.setHorizontalHeaderLabels(ls_columns)
        for tree in trees:
            row = []
            for col in ls_columns:
                value = database.db().get_str_value(tree.get(col, ""))
                item = QtGui.QStandardItem(value)
                row.append(item)
            #set the tree data and the icon (linking dead, present and the number of stems)
            row[0].setData(tree, role=QtCore.Qt.UserRole)
            row[0].setIcon(self.stems_icon(tree))
            self.model_trees.appendRow(row)
        self.window.tableView_trees.resizeColumnsToContents()
        header = self.window.tableView_trees.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)

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
        plot = database.PN_dbPlot(self.dbwidget)
    #initialize the registry database services
        database._registry = None
        database.init_registry(database.ServiceRegistry(self.dbwidget, plot=plot))
    #set the APG options into self.combo_taxa
    # dict_clades = database.dbtaxa().db_get_clades()
    #     lstclade = sorted(dict_clades.keys())
    #     for clade in lstclade:
    #         self.combo_taxa.addItem(clade, dict_clades[clade])
    #         # self.combo_taxa.addItem(clade)
    #         # self.combo_taxa.setItemData(self.combo_taxa.count() - 1, PNTaxa(0, clade), role=QtCore.Qt.UserRole)
            
    #     self.combo_taxa.setCurrentIndex(0)
    #     #set delegate for editing properties of PN_trview_identity & PN_trview_filter
    #     self.db_properties = taxa.db_dic_properties
    #     delegate = _EditProperties_Delegate(self.db_properties)
    #     self.trview_properties.setItemDelegate(delegate)
    #     self.trview_filter.setItemDelegate(delegate)
    #     self.trview_properties.setEditTriggers(QtWidgets.QAbstractItemView.CurrentChanged)
    #     self.trview_filter.setEditTriggers(QtWidgets.QAbstractItemView.CurrentChanged)
        
    #     #set the delegate and slots signals
    # #reconnect the signal to combo_taxa
    #     self.signal_combo_taxa(True)
    #     #self.combo_taxa.currentIndexChanged.connect(self.trview_taxonref_setData)
    # #set the ui enabled for the general widgets 
    #     self.refresh_ui_trview_taxonref(True)
    # #initialize the trview_taxonref (list of taxa)
    #     self.trview_filter_load()
    #     #self.trview_taxonref_setData()
    # def on_menu_theme_clicked(self, item):
    #     """GUI : Change the global theme of the UI through qss"""
    #     if item is None:
    #         item = "Diffnes"
    # #to change the theme        
    #     try:
    #         qss_path = f":src/florica/resources/qss/{item}.qss"
    #         file = QtCore.QFile(qss_path)
    #         if not file.open(QtCore.QIODevice.ReadOnly | QtCore.QIODevice.Text):
    #             raise RuntimeError(file.errorString())
    #         stream = QtCore.QTextStream(file)
    #         stylesheet = stream.readAll()
    #         file.close()
    #         QtWidgets.qApp.setStyleSheet(stylesheet)
    #         #self.style_history_slider()
    #         self.config_manager.theme = item
    #     except Exception as e:
    #         item = None
    #     #set the theme to the theme button
    #     self.view.buton_theme_text = item


    def close(self):
        """GUI: Close the main UI (mainwindow)"""
        self.window.close()

    def show(self):
        """GUI: Open the main UI (mainwindow)"""
        set_theme(
            self.config_manager,
            self.view.button_themes,
            self.config_manager.theme
        )
        #self.on_menu_theme_clicked (self.config_manager.theme)
        self.window.show()

def main():
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    controller = MainWindowController(window)
    controller.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
    