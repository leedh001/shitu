# ///////////////////////////////////////////////////////////////
#
# BY: WANDERSON M.PIMENTA
# PROJECT MADE WITH: Qt Designer and PySide6
# V: 1.0.0
#
# This project can be used freely for all uses, as long as they maintain the
# respective credits only in the Python scripts, any information in the visual
# interface (GUI) can be modified without any implication.
#
# There are limitations on Qt licenses if you want to use your products
# commercially, I recommend reading them on the official website:
# https://doc.qt.io/qtforpython/licenses.html
#
# ///////////////////////////////////////////////////////////////

# IMPORT QT CORE
# ///////////////////////////////////////////////////////////////
from qt_core import *

# IMPORT FUNCTIONS
# ///////////////////////////////////////////////////////////////
from gui.core.functions import *

# IMPORT SETTINGS
# ///////////////////////////////////////////////////////////////
from gui.core.json_settings import Settings

# IMPORT DIV
# ///////////////////////////////////////////////////////////////
from . py_div import PyDiv

# IMPORT BUTTON
# ///////////////////////////////////////////////////////////////
from . py_title_button import PyTitleButton

# GLOBALS
# ///////////////////////////////////////////////////////////////
_is_maximized = False
_old_size = QSize()

# PY TITLE BAR
# Top bar with move application, maximize, restore, minimize,
# close buttons and extra buttons
# ///////////////////////////////////////////////////////////////
class PyTitleBar(QWidget):
    # SIGNALS
    clicked = Signal(object)
    released = Signal(object)
    # 语义搜索：文本（strip 后）；空字符串表示清空筛选，恢复完整列表。
    semantic_search = Signal(str)

    def __init__(
        self,
        parent,
        app_parent,
        logo_image = "logo_top_100x22.svg",
        logo_width = 100,
        buttons = None,
        dark_one = "#1b1e23",
        bg_color = "#343b48",
        div_color = "#3c4454",
        btn_bg_color = "#343b48",
        btn_bg_color_hover = "#3c4454",
        btn_bg_color_pressed = "#2c313c",
        icon_color = "#c3ccdf",
        icon_color_hover = "#dce1ec",
        icon_color_pressed = "#edf0f5",
        icon_color_active = "#f5f6f9",
        context_color = "#6c99f4",
        text_foreground = "#8a95aa",
        radius = 8,
        font_family = "Segoe UI",
        title_size = 10,
        is_custom_title_bar = True,
    ):
        super().__init__()

        settings = Settings()
        self.settings = settings.items

        # PARAMETERS
        self._logo_image = logo_image
        self._dark_one = dark_one
        self._bg_color = bg_color
        self._div_color = div_color
        self._parent = parent
        self._app_parent = app_parent
        self._btn_bg_color = btn_bg_color
        self._btn_bg_color_hover = btn_bg_color_hover
        self._btn_bg_color_pressed = btn_bg_color_pressed  
        self._context_color = context_color
        self._icon_color = icon_color
        self._icon_color_hover = icon_color_hover
        self._icon_color_pressed = icon_color_pressed
        self._icon_color_active = icon_color_active
        self._font_family = font_family
        self._title_size = title_size
        self._text_foreground = text_foreground
        self._is_custom_title_bar = is_custom_title_bar

        # SETUP UI
        self.setup_ui()

        # ADD BG COLOR
        self.bg.setStyleSheet(f"background-color: {bg_color}; border-radius: {radius}px;")

        # SET LOGO AND WIDTH
        self.top_logo.setMinimumWidth(logo_width)
        self.top_logo.setMaximumWidth(logo_width)
        #self.top_logo.setPixmap(Functions.set_svg_image(logo_image))

        # MOVE WINDOW / MAXIMIZE / RESTORE
        # ///////////////////////////////////////////////////////////////
        def moveWindow(event):
            # IF MAXIMIZED CHANGE TO NORMAL
            if parent.isMaximized():
                self.maximize_restore()
                #self.resize(_old_size)
                curso_x = parent.pos().x()
                curso_y = event.globalPos().y() - QCursor.pos().y()
                parent.move(curso_x, curso_y)
            # MOVE WINDOW
            if event.buttons() == Qt.LeftButton:
                parent.move(parent.pos() + event.globalPos() - parent.dragPos)
                parent.dragPos = event.globalPos()
                event.accept()

        # MOVE APP WIDGETS (Leading / center strip / trailing strip)
        if is_custom_title_bar:
            self.leading_toolbar.mouseMoveEvent = moveWindow
            self.div_leading.mouseMoveEvent = moveWindow
            self.top_logo.mouseMoveEvent = moveWindow
            self.div_1.mouseMoveEvent = moveWindow
            self.title_label.mouseMoveEvent = moveWindow
            self.gallery_count_label.mouseMoveEvent = moveWindow
            self.semantic_pending_label.mouseMoveEvent = moveWindow
            self.semantic_indexed_label.mouseMoveEvent = moveWindow
            self.div_2.mouseMoveEvent = moveWindow
            self.trailing_toolbar.mouseMoveEvent = moveWindow
            self.div_3.mouseMoveEvent = moveWindow

        # MAXIMIZE / RESTORE
        if is_custom_title_bar:
            self.leading_toolbar.mouseDoubleClickEvent = self.maximize_restore
            self.div_leading.mouseDoubleClickEvent = self.maximize_restore
            self.top_logo.mouseDoubleClickEvent = self.maximize_restore
            self.div_1.mouseDoubleClickEvent = self.maximize_restore
            self.title_label.mouseDoubleClickEvent = self.maximize_restore
            self.gallery_count_label.mouseDoubleClickEvent = self.maximize_restore
            self.semantic_pending_label.mouseDoubleClickEvent = self.maximize_restore
            self.semantic_indexed_label.mouseDoubleClickEvent = self.maximize_restore
            self.div_2.mouseDoubleClickEvent = self.maximize_restore
            self.trailing_toolbar.mouseDoubleClickEvent = self.maximize_restore

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索…")
        self.search_input.setFixedHeight(28)              # 按你的标题栏高度调整
        self.search_input.setMinimumWidth(200)            # 可选
        # 让它优先“吃掉”多余空间（如果你希望它可伸缩）
        self.search_input.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )
        self.search_input.returnPressed.connect(self._on_search_enter)
        self.search_input.textChanged.connect(self._on_search_text_changed)
        self._search_debounce = QTimer(self)
        self._search_debounce.setSingleShot(True)
        self._search_debounce.setInterval(350)
        self._search_debounce.timeout.connect(self._emit_debounced_search)

        # ADD WIDGETS TO TITLE BAR
        # Regions: Leading | Center (logo, title, …) | Trailing | System (min/max/close)
        # ///////////////////////////////////////////////////////////////
        self.bg_layout.addWidget(self.leading_toolbar)
        self.bg_layout.addWidget(self.div_leading)
        self.bg_layout.addWidget(self.top_logo)
        self.bg_layout.addWidget(self.div_1)
        self.bg_layout.addWidget(self.title_label)
        self.bg_layout.addWidget(self.gallery_count_label)
        self.bg_layout.addWidget(self.semantic_pending_label)
        self.bg_layout.addWidget(self.semantic_indexed_label)
        self.bg_layout.addWidget(self.search_input, 1, Qt.AlignVCenter)
        self.bg_layout.addWidget(self.div_2)
        self.bg_layout.addWidget(self.trailing_toolbar)

        # ADD BUTTONS BUTTONS
        # ///////////////////////////////////////////////////////////////
        # Functions
        self.minimize_button.released.connect(lambda: parent.showMinimized())
        self.maximize_restore_button.released.connect(lambda: self.maximize_restore())
        self.close_button.released.connect(lambda: parent.close())

        # ADD Buttons
        if is_custom_title_bar:            
            self.bg_layout.addWidget(self.minimize_button)
            self.bg_layout.addWidget(self.maximize_restore_button)
            self.bg_layout.addWidget(self.close_button)

        # Until add_left_menus / add_right_menus run, toolbars are empty — hide chrome
        self._sync_leading_region_visibility()
        self._sync_trailing_region_visibility()

    def _create_title_menu_button(self, parameter):
        _btn_icon = Functions.set_svg_icon(parameter['btn_icon'])
        _btn_id = parameter['btn_id']
        _btn_tooltip = parameter['btn_tooltip']
        _is_active = parameter['is_active']
        btn = PyTitleButton(
            self._parent,
            self._app_parent,
            btn_id = _btn_id,
            tooltip_text = _btn_tooltip,
            dark_one = self._dark_one,
            bg_color = self._bg_color,
            bg_color_hover = self._btn_bg_color_hover,
            bg_color_pressed = self._btn_bg_color_pressed,
            icon_color = self._icon_color,
            icon_color_hover = self._icon_color_active,
            icon_color_pressed = self._icon_color_pressed,
            icon_color_active = self._icon_color_active,
            context_color = self._context_color,
            text_foreground = self._text_foreground,
            icon_path = _btn_icon,
            is_active = _is_active
        )
        btn.clicked.connect(self.btn_clicked)
        btn.released.connect(self.btn_released)
        return btn

    def _sync_leading_region_visibility(self):
        has = self.leading_buttons_layout.count() > 0
        self.leading_toolbar.setVisible(has)
        self.div_leading.setVisible(has)

    def _sync_trailing_region_visibility(self):
        has = self.trailing_buttons_layout.count() > 0
        self.trailing_toolbar.setVisible(has)

    # Leading toolbar (leftmost): workspace and future actions
    # ///////////////////////////////////////////////////////////////
    def add_left_menus(self, parameters):
        if parameters is None or len(parameters) == 0:
            self._sync_leading_region_visibility()
            return
        for parameter in parameters:
            self.leading_buttons_layout.addWidget(self._create_title_menu_button(parameter))
        self._sync_leading_region_visibility()

    # Trailing toolbar: search, settings, … + divider before window controls
    # ///////////////////////////////////////////////////////////////
    def add_right_menus(self, parameters):
        if parameters is None or len(parameters) == 0:
            self._sync_trailing_region_visibility()
            return
        for parameter in parameters:
            self.trailing_buttons_layout.addWidget(self._create_title_menu_button(parameter))
        if self._is_custom_title_bar:
            self.trailing_buttons_layout.addWidget(self.div_3)
        self._sync_trailing_region_visibility()

    # Backward-compatible alias: same as add_right_menus
    def add_menus(self, parameters):
        self.add_right_menus(parameters)

    # TITLE BAR MENU EMIT SIGNALS
    # ///////////////////////////////////////////////////////////////
    def btn_clicked(self):
        self.clicked.emit(self.sender())

    def btn_released(self):
        self.released.emit(self.sender())

    # SET TITLE BAR TEXT
    # ///////////////////////////////////////////////////////////////
    def set_title(self, title):
        self.title_label.setText(title)

    def set_gallery_count(self, count: int):
        self.gallery_count_label.setText(f"{count} 张")

    def set_semantic_index_counts(self, pending: int, indexed: int) -> None:
        """待索引队列剩余数量 / 已在向量库中的数量（加载时跳过的有效条数 + 本轮成功写入）。"""
        self.semantic_pending_label.setText(f"待索引 {int(pending)} 张")
        self.semantic_indexed_label.setText(f"已索引 {int(indexed)} 张")

    # MAXIMIZE / RESTORE
    # maximize and restore parent window
    # ///////////////////////////////////////////////////////////////
    def maximize_restore(self, e = None):
        global _is_maximized
        global _old_size
        
        # CHANGE UI AND RESIZE GRIP
        def change_ui():
            if _is_maximized:
                self._parent.ui.central_widget_layout.setContentsMargins(0,0,0,0)
                self._parent.ui.window.set_stylesheet(border_radius = 0, border_size = 0)
                self.maximize_restore_button.set_icon(
                    Functions.set_svg_icon("icon_restore.svg")
                )
            else:
                self._parent.ui.central_widget_layout.setContentsMargins(10,10,10,10)
                self._parent.ui.window.set_stylesheet(border_radius = 10, border_size = 2)
                self.maximize_restore_button.set_icon(
                    Functions.set_svg_icon("icon_maximize.svg")
                )

        # CHECK EVENT
        if self._parent.isMaximized():
            _is_maximized = False
            self._parent.showNormal()
            change_ui()
        else:
            _is_maximized = True
            _old_size = QSize(self._parent.width(), self._parent.height())
            self._parent.showMaximized()
            change_ui()

    def _on_search_enter(self):
        self._search_debounce.stop()
        self.semantic_search.emit(self.search_input.text().strip())

    def _on_search_text_changed(self):
        self._search_debounce.start()

    def _emit_debounced_search(self):
        self.semantic_search.emit(self.search_input.text().strip())

    # SETUP APP
    # ///////////////////////////////////////////////////////////////
    def setup_ui(self):
        # ADD MENU LAYOUT
        self.title_bar_layout = QVBoxLayout(self)
        self.title_bar_layout.setContentsMargins(0,0,0,0)

        # ADD BG
        self.bg = QFrame()

        # ADD BG LAYOUT
        self.bg_layout = QHBoxLayout(self.bg)
        self.bg_layout.setContentsMargins(10,0,5,0)
        self.bg_layout.setSpacing(0)

        # DIVS
        self.div_leading = PyDiv(self._div_color)
        self.div_1 = PyDiv(self._div_color)
        self.div_2 = PyDiv(self._div_color)
        self.div_3 = PyDiv(self._div_color)

        # Leading / trailing toolbars (extra title bar buttons)
        self.leading_toolbar = QWidget()
        self.leading_buttons_layout = QHBoxLayout(self.leading_toolbar)
        self.leading_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.leading_buttons_layout.setSpacing(3)

        self.trailing_toolbar = QWidget()
        self.trailing_buttons_layout = QHBoxLayout(self.trailing_toolbar)
        self.trailing_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.trailing_buttons_layout.setSpacing(3)

        # Toolbars only as wide as their buttons (do not absorb extra horizontal space)
        _sp = QSizePolicy.Policy
        self.leading_toolbar.setSizePolicy(_sp.Maximum, _sp.Preferred)
        self.trailing_toolbar.setSizePolicy(_sp.Maximum, _sp.Preferred)

        # LEFT FRAME WITH MOVE APP
        self.top_logo = QLabel()
        self.top_logo_layout = QVBoxLayout(self.top_logo)
        self.top_logo_layout.setContentsMargins(0,0,0,0)
        self.logo_svg = QSvgWidget()
        self.logo_svg.load(Functions.set_svg_image(self._logo_image))
        self.top_logo_layout.addWidget(self.logo_svg, Qt.AlignCenter, Qt.AlignCenter)

        # TITLE LABEL
        self.title_label = QLabel()
        self.title_label.setAlignment(Qt.AlignVCenter)
        self.title_label.setStyleSheet(f'font: {self._title_size}pt "{self._font_family}"')

        # GALLERY IMAGE COUNT
        self.gallery_count_label = QLabel()
        self.gallery_count_label.setAlignment(Qt.AlignVCenter)
        self.gallery_count_label.setStyleSheet(
            f'font: {self._title_size}pt "{self._font_family}"; color: {self._text_foreground}; margin-left: 12px;'
        )

        _semantic_style = (
            f'font: {self._title_size}pt "{self._font_family}"; color: {self._text_foreground}; margin-left: 10px;'
        )
        self.semantic_pending_label = QLabel()
        self.semantic_pending_label.setAlignment(Qt.AlignVCenter)
        self.semantic_pending_label.setStyleSheet(_semantic_style)
        self.semantic_pending_label.setText("待索引 0 张")
        self.semantic_indexed_label = QLabel()
        self.semantic_indexed_label.setAlignment(Qt.AlignVCenter)
        self.semantic_indexed_label.setStyleSheet(_semantic_style)
        self.semantic_indexed_label.setText("已索引 0 张")

        # MINIMIZE BUTTON
        self.minimize_button = PyTitleButton(
            self._parent,
            self._app_parent,
            tooltip_text = "Close app",
            dark_one = self._dark_one,
            bg_color = self._btn_bg_color,
            bg_color_hover = self._btn_bg_color_hover,
            bg_color_pressed = self._btn_bg_color_pressed,
            icon_color = self._icon_color,
            icon_color_hover = self._icon_color_hover,
            icon_color_pressed = self._icon_color_pressed,
            icon_color_active = self._icon_color_active,
            context_color = self._context_color,
            text_foreground = self._text_foreground,
            radius = 6,
            icon_path = Functions.set_svg_icon("icon_minimize.svg")
        )

        # MAXIMIZE / RESTORE BUTTON
        self.maximize_restore_button = PyTitleButton(
            self._parent,
            self._app_parent,
            tooltip_text = "Maximize app",
            dark_one = self._dark_one,
            bg_color = self._btn_bg_color,
            bg_color_hover = self._btn_bg_color_hover,
            bg_color_pressed = self._btn_bg_color_pressed,
            icon_color = self._icon_color,
            icon_color_hover = self._icon_color_hover,
            icon_color_pressed = self._icon_color_pressed,
            icon_color_active = self._icon_color_active,
            context_color = self._context_color,
            text_foreground = self._text_foreground,
            radius = 6,
            icon_path = Functions.set_svg_icon("icon_maximize.svg")
        )

        # CLOSE BUTTON
        self.close_button = PyTitleButton(
            self._parent,
            self._app_parent,
            tooltip_text = "Close app",
            dark_one = self._dark_one,
            bg_color = self._btn_bg_color,
            bg_color_hover = self._btn_bg_color_hover,
            bg_color_pressed = self._context_color,
            icon_color = self._icon_color,
            icon_color_hover = self._icon_color_hover,
            icon_color_pressed = self._icon_color_active,
            icon_color_active = self._icon_color_active,
            context_color = self._context_color,
            text_foreground = self._text_foreground,
            radius = 6,
            icon_path = Functions.set_svg_icon("icon_close.svg")
        )

        # ADD TO LAYOUT
        self.title_bar_layout.addWidget(self.bg)