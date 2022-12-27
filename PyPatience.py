# ******************************************************************************
#
#                               PyPatience
#
#                              Version  1.0
#
# ******************************************************************************
APPLICATION_NAME = "PyPatience"
APPLICATION_VERSION = "1.0.0.0"

import math
import random
import os
import copy

from PyQt6.QtGui import *
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *


# ------------------------------------------------------------------------------
# CONSTANTS
# ------------------------------------------------------------------------------

SUIT_NONE = 0
SUIT_CLUBS = 1
SUIT_DIAMONDS = 2
SUIT_HEARTS = 3
SUIT_SPADES = 4

CARD_COLOR_RED = 0
CARD_COLOR_BLACK = 1

DECK_RED = 0
DECK_BLUE = 1

CARD_RATIO = 485 / 334

ACE = 1
KING = 13


# --------------------------------------------------------------------------------
# CARD
# --------------------------------------------------------------------------------

class Card:

    def __init__(self, suit, value, pixmap):
        self.suit = suit
        self.value = value     # [1,13]
        self.image = pixmap    # QPixmap
        self.face_up = True
        
    def color(self):
        if self.suit == SUIT_CLUBS or self.suit == SUIT_SPADES:
            return CARD_COLOR_BLACK
        return CARD_COLOR_RED


# --------------------------------------------------------------------------------
# PILE
# --------------------------------------------------------------------------------

class Pile:
    
    def __init__(self, tableau, index=0):
        self.index = index
        self.tableau = tableau
        self.cards = []
        self.rect = QRect()
        self.visibility = 0.12   # value [0,1] that determines how visible an underlying card is

    def draw_card_back(self, qpainter, qrect):
        qpainter.save()
        pen = QPen()
        qpainter.setPen(pen)
        back_color = QColorConstants.Red
        if self.tableau.deck == DECK_BLUE:
            back_color = QColorConstants.Blue
        qpainter.setBrush(QBrush(back_color, style=Qt.BrushStyle.DiagCrossPattern))
        border = round(qrect.width() * 0.07)
        r = qrect.adjusted(border, border, -border, -border)
        pen.setStyle(Qt.PenStyle.NoPen)
        qpainter.setPen(pen)
        t = round(r.width() * 0.06)
        qpainter.drawRoundedRect(r, t, t)
        qpainter.restore()

    def draw_pile(self, qpainter):
        if len(self.cards) == 0:
            return
        qpainter.save()
        qpainter.setBrush(QBrush(QColor(255,255,255)))
        qpainter.setPen(QPen())
        r = copy.copy(self.rect)
        i = 0
        if self.visibility == 0.0:
            # draw only last/top card
            i = len(self.cards) - 1
        while i < len(self.cards):
            self.get_card_rect(r, i)
            t =  round(r.width() * 0.06)
            qpainter.drawRoundedRect(r, t, t)   # filled rounded rect
            pixmap_rect = scale_rect_around_center(r, 0.95)
            if self.cards[i].face_up:
                qpainter.drawPixmap(pixmap_rect, self.cards[i].image)
            else:
                self.draw_card_back(qpainter, r)
            i += 1
        qpainter.restore()

    def get_card_rect(self, card_rect, card_index):
        card_rect.setX(self.rect.x())
        card_rect.setY(self.rect.y())
        card_rect.setWidth(self.rect.width())
        card_rect.setHeight(self.rect.height())
        if self.visibility == 0:
            return
        translate_y = 0
        i = 0
        while i < card_index:
            if self.cards[i].face_up and self.cards[i + 1].face_up:
                translate_y = round(self.rect.width() * self.visibility)
            else:
                translate_y = max(round(self.rect.width() * self.visibility / 3), 2)
            card_rect.translate(0, translate_y)
            i += 1
            
    def get_card_at(self, x, y):
        r = QRect()
        i = len(self.cards) - 1
        while i >= 0:
            self.get_card_rect(r, i)
            if r.contains(x, y):
                return i
            i -= 1
        return -1

    def split(self, card_index):
        new_pile = Pile(self.tableau)
        new_pile.rect = QRect()
        self.get_card_rect(new_pile.rect, card_index)
        new_pile.cards = self.cards[card_index:]
        new_pile.visibility = self.visibility
        del self.cards[-len(self.cards) + card_index:]
        return new_pile

    def move(self, dx, dy):
        self.rect.translate(dx, dy)

    def append(self, pile):
        self.cards.extend(pile.cards)

    def is_empty(self):
        return len(self.cards) == 0

    def is_top_card(self, card_index):
        return (card_index >= 0) and (card_index == len(self.cards) - 1)

    def clear(self):
        self.cards.clear()

    def push_back(self, card):
        self.cards.append(card)

    def pop(self):
        return self.cards.pop()

    def push_front(self, card):
        self.cards.insert(0, card)

    def top(self):
        return self.cards[-1]

    def size(self):
        return len(self.cards)

    def front(self):
        return self.cards[0]
    
def scale_rect_around_center(qrect, factor):
    new_rect = copy.copy(qrect)
    new_rect.setWidth(round(qrect.width() * factor))
    new_rect.setHeight(round(qrect.height() * factor))
    new_rect.translate(round((qrect.width() - new_rect.width()) / 2),
                       round((qrect.height() - new_rect.height()) / 2))
    return new_rect


# --------------------------------------------------------------------------------
# TABLEAU
# --------------------------------------------------------------------------------

class Tableau(QWidget):

    def __init__(self):
        super().__init__()
        self.cards = None
        self.piles = []
        for i in range(13):
            self.piles.append(Pile(self, i))
        for i in range(6):
            self.piles[i].visibility = 0.0
        self.temp_pile = None   # pile used to drag and drop
        self.old_x = 0
        self.old_y = 0
        self.source_pile = None
        self.target_pile = None
        self.deck = DECK_RED
        self.undo_string = ""
        self.zoom_factor = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.recalc_layout()
        
    def deal(self):
        for pile in self.piles:
            pile.clear()
        random.shuffle(self.cards)
        self.undo_string = ""
        k = 0
        i = 0
        while i < 7:
            for j in range(i + 1):
                self.cards[k].face_up = i == j
                self.piles[i + 6].push_back(self.cards[k])
                k += 1
            i += 1
        while k < 52:
            self.cards[k].face_up = False
            self.piles[0].push_back(self.cards[k])
            k += 1
        self.repaint()

    def move_cards(self, index1, index2, n, turn=False):
        # Move n cards from piles[index1] to piles[index2].
        i = 0
        while i < n:
            card = self.piles[index1].pop()
            if turn:
                card.face_up = not card.face_up
            self.piles[index2].push_back(card)
            i += 1
            
    def undo(self):
        lst = self.undo_string.split(':')
        if len(lst) == 0:
            return
        if  lst[0] == "move-cards":
            # move-cards: <from> <to> <# cards>
            args = lst[1].split()
            self.move_cards(int(args[1]), int(args[0]), int(args[2]))
            self.undo_string = ""
            self.repaint()
        elif lst[0] == "stock-to-waste":
            card = self.piles[1].pop()
            card.face_up = False
            self.piles[0].push_back(card)
            self.undo_string = ""
            self.repaint()
        elif lst[0] == "waste-to-stock":
            self.move_cards(0, 1, self.piles[0].size(), True)
            self.undo_string = ""
            self.repaint()
        return
            
    def recalc_layout(self):
        card_width = round(self.fontMetrics().height() * 8 * self.zoom_factor)
        card_height = round(card_width * CARD_RATIO)
        border_width = card_width // 5
        x = border_width + self.offset_x
        y = border_width + self.offset_y
        i = 0
        while i < len(self.piles):
            self.piles[i].rect.setRect(x, y, card_width, card_height)
            if i == 1:
                x += 2 * (card_width + border_width)
            elif i == 5:
                x = border_width + self.offset_x
                y += card_height + border_width
            else:
                x += card_width + border_width
            i += 1

    def draw_background(self, qpainter):
        qpainter.save()
        qpainter.setBrush(QBrush(QColor(0,128,0)))
        qpainter.drawRect(self.rect())
        qpainter.restore()

    def resizeEvent(self, event):
        self.recalc_layout()
        QWidget.resizeEvent(self, event)

    def draw_foundations(self, qpainter):
        qpainter.save()
        pen = QPen()
        pen.setStyle(Qt.PenStyle.NoPen)
        qpainter.setPen(pen)
        qpainter.setBrush(QBrush(QColor(0,0,0), style=Qt.BrushStyle.Dense6Pattern))
        for i in range(2, 6):
            r = self.piles[i].rect
            t = round(r.width() * 0.06)
            qpainter.drawRoundedRect(r, t, t)
        qpainter.restore()

    def draw_stock_background(self, qpainter):
        qpainter.save()
        pen = QPen()
        qpainter.setPen(pen)
        r = self.piles[0].rect
        t = round(r.width() * 0.06)
        qpainter.drawRoundedRect(r, t, t)
        w = round(r.width() * 0.75)
        x = r.x() + (r.width() - w) // 2
        y = r.y() + (r.height() - w) // 2
        pen.setWidth(round(w * 0.15))
        pen.setColor(QColor(255,255,255,16))
        qpainter.setPen(pen)
        qpainter.drawEllipse(x, y, w, w)
        qpainter.restore()

    def paintEvent(self, event):
        qpainter = QPainter(self)
        qpainter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform|QPainter.RenderHint.Antialiasing)
        self.draw_background(qpainter)
        self.draw_foundations(qpainter)
        self.draw_stock_background(qpainter)
        for pile in self.piles:
            pile.draw_pile(qpainter)
        if self.temp_pile is not None:
            self.temp_pile.draw_pile(qpainter)

    def mousePressEvent(self, event):
        # mouseReleaseEvent will do a repaint.
        if event.button() == Qt.MouseButton.LeftButton:
            x = int(event.position().x())
            y = int(event.position().y())
            self.old_x = x
            self.old_y = y
            pile, card_index = self.get_pile_and_card_at(x, y)
            if pile is not None:
                if pile.index == 0:
                    # stock
                    if pile.size() > 0:
                        top_card = pile.pop()
                        top_card.face_up = True
                        self.piles[1].push_back(top_card)
                        self.undo_string = "stock-to-waste"
                    else:
                        for card in self.piles[1].cards:
                            card.face_up = False
                            self.piles[0].push_front(card)
                        self.piles[1].clear()
                        self.undo_string = "waste-to-stock"
                else:
                    if card_index != -1:
                        if not pile.top().face_up:
                            pile.top().face_up = True
                            self.undo_string = ""
                        else:
                            self.temp_pile = pile.split(card_index)
                            self.source_pile = pile

    def is_valid_target_pile(self, pile):
        # This function is only used with drag and drop, not
        # when double clicking.
        if pile.index < 2:
            # pile is stock or waste
            return False
        if pile.index <= 5:
            # pile is a foundation
            if self.temp_pile.size() == 1:
                if pile.is_empty():
                    # return true if we have an ace
                    return self.temp_pile.top().value == ACE
                else:
                    card1 = pile.top()
                    card2 = self.temp_pile.top()
                    return (card1.suit == card2.suit) and \
                           (card1.value == card2.value - 1)
            else:
                # cannot put two or more cards on a foundation
                return False
        if pile.size() == 0:
            return self.temp_pile.front().value == KING
        card1 = pile.top()
        card2 = self.temp_pile.front()
        return (card1.color() != card2.color()) and \
               (card1.value == card2.value + 1)
    
    def mouseMoveEvent(self, event):
        if self.temp_pile is not None:
            # Move pile.
            x = int(event.position().x())
            y = int(event.position().y())
            dx = x - self.old_x
            dy = y - self.old_y
            self.temp_pile.move(dx, dy)
            self.old_x = x
            self.old_y = y
            # Find target pile.
            self.target_pile = None
            rect = QRect()
            self.temp_pile.get_card_rect(rect, 0)
            center_x = rect.x() + rect.width() // 2
            center_y = rect.y() + rect.height() // 2
            for pile in self.piles:
                pile.get_card_rect(rect, len(pile.cards) - 1)
                if rect.contains(center_x, center_y):
                    if self.is_valid_target_pile(pile):
                        self.target_pile = pile
            self.repaint()
        elif event.buttons() & Qt.MouseButton.LeftButton:
            x = int(event.position().x())
            y = int(event.position().y())
            dx = x - self.old_x
            dy = y - self.old_y
            self.offset_x += dx
            self.offset_y += dy
            self.old_x = x
            self.old_y = y
            self.recalc_layout()
            self.repaint()
                 
    def mouseReleaseEvent(self, event):
        if self.temp_pile is not None:
            if self.target_pile is not None:
                self.target_pile.append(self.temp_pile)
                self.undo_string = "move-cards: %d %d %d" % \
                                   (self.source_pile.index, self.target_pile.index,\
                                    self.temp_pile.size())
            else:
                self.source_pile.append(self.temp_pile)
            self.source_pile = None
            self.temp_pile = None
            self.target_pile = None
        self.repaint()

    def get_pile_and_card_at(self, x, y):
        # This function can return a pile and a
        # card_index of -1 if the pile is empty.
        for pile in self.piles:
            card_index = pile.get_card_at(x, y)
            if card_index != -1:
                return pile, card_index
            if pile.rect.contains(x, y):
                return pile, -1
        return None, -1

    def get_target_foundation(self, card1):
        if card1.value == 1:
            # if ace, find first empty foundation
            i = 2
            while i <= 5:
                pile = self.piles[i]
                if pile.size() == 0:
                    return pile
                i += 1
        else:
            # find foundation of same suit
            i = 2
            while i <= 5:
                pile = self.piles[i]
                if pile.size() > 0:
                    card2 = pile.top()
                    if (card1.suit == card2.suit) and \
                       (card1.value == card2.value + 1):
                        return pile
                i += 1
        return None

    def mouseDoubleClickEvent(self, event):
        x = int(event.position().x())
        y = int(event.position().y())
        pile, card_index = self.get_pile_and_card_at(x, y)
        if pile is not None and \
           pile.index in (1, 6, 7, 8, 9, 10, 11, 12) and \
           pile.is_top_card(card_index):
            # we have only one card, find target pile and
            # let release event handle actual move
            self.temp_pile = pile.split(card_index)
            self.source_pile = pile
            self.target_pile = self.get_target_foundation(self.temp_pile.front())

    def set_zoom_factor(self, factor):
        # 0.1 cannot be represented exactly in IEEE 754 floating point, so we
        # have to use round(factor, 1) to avoid weird behavior.
        self.zoom_factor = round(factor, 1)
        if self.zoom_factor <= 0.0:
            self.zoom_factor = 0.1
        elif self.zoom_factor > 10.0:
            self.zoom_factor = 10.0
        self.recalc_layout()
        self.repaint()


# --------------------------------------------------------------------------------
# MAINWINDOW
# --------------------------------------------------------------------------------

class MainWindow(QMainWindow):
    
    def __init__(self):
        super().__init__()
        self.setStyleSheet("font-size: 10pt;")
        # Tableau must be initialized before calling load_settings()!
        self.tableau = Tableau()
        self.load_settings()
        self.init_ui()
        self.load_cards()
        self.tableau.deal()
        self.setWindowTitle("PyPatience")
        self.setWindowIcon(QIcon("PyPatience.ico"))
        self.show()

    def init_ui(self):
        self.setCentralWidget(self.tableau)
        menu_bar = self.menuBar()
        # ------- Game -------
        game_menu = menu_bar.addMenu("&Game")
        game_menu.aboutToShow.connect(self.game_menu_about_to_show)
        # ------- Deal -------
        menu_item = QAction("&Deal", self)
        menu_item.triggered.connect(self.on_game_deal)
        game_menu.addAction(menu_item)
        game_menu.addSeparator()
        # ------- Undo -------
        self.undo_action = QAction("&Undo", self)
        self.undo_action.triggered.connect(self.on_game_undo)
        game_menu.addAction(self.undo_action)
        # ------- Deck -------
        deck_menu = game_menu.addMenu("De&ck")
        menu_item_red = QAction("&Red", self)
        menu_item_red.setCheckable(True)
        menu_item_red.setChecked(self.tableau.deck == DECK_RED)
        menu_item_red.triggered.connect(self.on_game_deck_red)
        menu_item_blue = QAction("&Blue", self)
        menu_item_blue.setCheckable(True)
        menu_item_blue.setChecked(self.tableau.deck == DECK_BLUE)
        menu_item_blue.triggered.connect(self.on_game_deck_blue)
        deck_menu.addAction(menu_item_red)
        deck_menu.addAction(menu_item_blue)
        deck_group = QActionGroup(self)
        deck_group.addAction(menu_item_red)
        deck_group.addAction(menu_item_blue)
        game_menu.addMenu(deck_menu)
        # ------- Exit -------
        game_menu.addSeparator()
        menu_item = QAction("E&xit", self)
        menu_item.triggered.connect(self.close)
        game_menu.addAction(menu_item)
        # ------- View -------
        view_menu = menu_bar.addMenu("&View")
        menu_item = QAction("Zoom &In", self)
        menu_item.setShortcut("+")
        menu_item.triggered.connect(self.on_view_zoom_in)
        view_menu.addAction(menu_item)
        menu_item = QAction("Zoom &Out", self)
        menu_item.setShortcut("-")
        menu_item.triggered.connect(self.on_view_zoom_out)
        view_menu.addAction(menu_item)
        menu_item = QAction("&Normal Size", self)
        menu_item.triggered.connect(self.on_view_zoom_normal_size)
        view_menu.addAction(menu_item)
        # ------- Help -------
        help_menu = menu_bar.addMenu("&Help")
        # ------- About -------
        menu_item = QAction("&About...", self)
        menu_item.triggered.connect(self.on_help_about)
        help_menu.addAction(menu_item)

    def game_menu_about_to_show(self):
        self.undo_action.setEnabled(len(self.tableau.undo_string) > 0) 
     
    def on_game_deal(self, s):
        self.tableau.deal()

    def on_game_undo(self, s):
        self.tableau.undo()
        
    def on_game_deck_red(self, s):
        self.tableau.deck = DECK_RED
        self.tableau.repaint()

    def on_game_deck_blue(self, s):
        self.tableau.deck = DECK_BLUE
        self.tableau.repaint()

    def wheelEvent(self, event):
        self.tableau.set_zoom_factor(self.tableau.zoom_factor + event.angleDelta().y() / 300)

    def on_view_zoom_in(self, s):
        self.tableau.set_zoom_factor(self.tableau.zoom_factor + 0.1)

    def on_view_zoom_out(self, s):
        self.tableau.set_zoom_factor(self.tableau.zoom_factor - 0.1)

    def on_view_zoom_normal_size(self, s):
        self.tableau.set_zoom_factor(1.0)
    
    def on_help_about(self, s):
        QMessageBox.aboutQt(self, "PyPatience")
        
    def load_settings(self):
        settings = QSettings("PyPatience", "PyPatience")
        self.resize(settings.value("size", QSize(800, 600)))
        self.move(settings.value("pos", QPoint(0, 0)))
        self.tableau.deck = settings.value("deck", DECK_RED)

    def save_settings(self):
        settings = QSettings("PyPatience", "PyPatience")
        settings.setValue("size", self.size())
        settings.setValue("pos", self.pos())
        settings.setValue("deck", self.tableau.deck)

    def load_cards(self):

        def load_suit(cards, s):
            suit_filenames = {
                SUIT_CLUBS:     "clubs",
                SUIT_DIAMONDS:  "diamonds",
                SUIT_HEARTS:    "hearts",
                SUIT_SPADES:    "spades"
                }
            suit_filename = suit_filenames[s]
            for i in range(13):
                card = Card(s, i + 1, QPixmap(
                    f"{os.getcwd()}{os.path.sep}cards{os.path.sep}{suit_filename} {i + 1}.png"))
                cards.append(card)

        cards = []
        load_suit(cards, SUIT_CLUBS)
        load_suit(cards, SUIT_DIAMONDS)
        load_suit(cards, SUIT_HEARTS)
        load_suit(cards, SUIT_SPADES)
        self.tableau.cards = cards
        
    def closeEvent(self, event):
        self.save_settings()


# --------------------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------------------

def main():
    app = QApplication([])
    app.setApplicationName(APPLICATION_NAME)
    app.setApplicationVersion(APPLICATION_VERSION)
    main_window = MainWindow()
    main_window.show()
    app.exec()

if __name__ == "__main__":
    main()


