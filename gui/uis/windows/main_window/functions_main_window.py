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

# IMPORT PACKAGES AND MODULES
# ///////////////////////////////////////////////////////////////
import sys

# IMPORT QT CORE
# ///////////////////////////////////////////////////////////////
from qt_core import *

# LOAD UI MAIN
# ///////////////////////////////////////////////////////////////
from . ui_main import *

# FUNCTIONS
class MainFunctions():
    def __init__(self):
        super().__init__()
        # SETUP MAIN WINDOw
        # Load widgets from "gui\uis\main_window\ui_main.py"
        # ///////////////////////////////////////////////////////////////
        self.ui = UI_MainWindow()
        self.ui.setup_ui(self)

    # SET MAIN WINDOW PAGES
    # ///////////////////////////////////////////////////////////////
    def set_page(self, page):
        self.ui.load_pages.pages.setCurrentWidget(page)

    # SET LEFT COLUMN PAGES
    # ///////////////////////////////////////////////////////////////
    def set_left_column_menu(
        self,
        menu,
        title,
        icon_path
    ):
        self.ui.left_column.menus.menus.setCurrentWidget(menu)
        self.ui.left_column.title_label.setText(title)
        self.ui.left_column.icon.set_icon(icon_path)

    # RETURN IF LEFT COLUMN IS VISIBLE
    # ///////////////////////////////////////////////////////////////
    def left_column_is_visible(self):
        width = self.ui.left_column_frame.width()
        if width == 0:
            return False
        else:
            return True

    # RETURN IF RIGHT COLUMN IS VISIBLE
    # ///////////////////////////////////////////////////////////////
    def right_column_is_visible(self):
        width = self.ui.right_column_frame.width()
        if width == 0:
            return False
        else:
            return True

    # SET RIGHT COLUMN PAGES
    # ///////////////////////////////////////////////////////////////
    def set_right_column_menu(self, menu):
        self.ui.right_column.menus.setCurrentWidget(menu)

    # GET TITLE BUTTON BY OBJECT NAME
    # ///////////////////////////////////////////////////////////////
    def get_title_bar_btn(self, object_name):
        return self.ui.title_bar_frame.findChild(QPushButton, object_name)

    # GET TITLE BUTTON BY OBJECT NAME
    # ///////////////////////////////////////////////////////////////
    def get_left_menu_btn(self, object_name):
        # Left icon rail removed; kept for callers that optionally clear tab state.
        if hasattr(self.ui, "left_menu"):
            return self.ui.left_menu.findChild(QPushButton, object_name)
        return None
    
    # LEDT AND RIGHT COLUMNS / SHOW / HIDE
    # ///////////////////////////////////////////////////////////////
    def toggle_left_column(self):
        # GET ACTUAL CLUMNS SIZE
        width = self.ui.left_column_frame.width()
        right_column_width = self.ui.right_column_frame.width()

        MainFunctions.start_box_animation(self, width, right_column_width, "left")

    def toggle_right_column(self):
        # GET ACTUAL CLUMNS SIZE
        left_column_width = self.ui.left_column_frame.width()
        width = self.ui.right_column_frame.width()

        MainFunctions.start_box_animation(self, left_column_width, width, "right")

    def start_box_animation(self, left_box_width, right_box_width, direction):
        right_width = 0
        left_width = 0
        time_animation = self.ui.settings["time_animation"]
        minimum_left = self.ui.settings["left_column_size"]["minimum"]
        maximum_left = self.ui.settings["left_column_size"]["maximum"]
        minimum_right = self.ui.settings["right_column_size"]["minimum"]
        maximum_right = self.ui.settings["right_column_size"]["maximum"]

        # Check Left Values        
        if left_box_width == minimum_left and direction == "left":
            left_width = maximum_left
        else:
            left_width = minimum_left

        # Check Right values        
        if right_box_width == minimum_right and direction == "right":
            right_width = maximum_right
        else:
            right_width = minimum_right

        lf = self.ui.left_column_frame
        rf = self.ui.right_column_frame
        # Columns use min==max when open or closed; animate both or max can block collapse
        # (e.g. startup sets right min=max=240; only animating min to 0 leaves max=240).

        # ANIMATION LEFT BOX
        self.left_box = QPropertyAnimation(lf, b"minimumWidth")
        self.left_box.setDuration(time_animation)
        self.left_box.setStartValue(lf.minimumWidth())
        self.left_box.setEndValue(left_width)
        self.left_box.setEasingCurve(QEasingCurve.InOutQuart)

        self.left_box_max = QPropertyAnimation(lf, b"maximumWidth")
        self.left_box_max.setDuration(time_animation)
        self.left_box_max.setStartValue(lf.maximumWidth())
        self.left_box_max.setEndValue(left_width)
        self.left_box_max.setEasingCurve(QEasingCurve.InOutQuart)

        # ANIMATION RIGHT BOX
        self.right_box = QPropertyAnimation(rf, b"minimumWidth")
        self.right_box.setDuration(time_animation)
        self.right_box.setStartValue(rf.minimumWidth())
        self.right_box.setEndValue(right_width)
        self.right_box.setEasingCurve(QEasingCurve.InOutQuart)

        self.right_box_max = QPropertyAnimation(rf, b"maximumWidth")
        self.right_box_max.setDuration(time_animation)
        self.right_box_max.setStartValue(rf.maximumWidth())
        self.right_box_max.setEndValue(right_width)
        self.right_box_max.setEasingCurve(QEasingCurve.InOutQuart)

        # GROUP ANIMATION
        self.group = QParallelAnimationGroup()
        self.group.stop()
        self.group.addAnimation(self.left_box)
        self.group.addAnimation(self.left_box_max)
        self.group.addAnimation(self.right_box)
        self.group.addAnimation(self.right_box_max)
        self.group.start()