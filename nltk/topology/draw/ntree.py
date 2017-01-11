from tkinter import *
from tkinter.ttk import *

from nltk.draw.util import CanvasWidget
from nltk.topology import FeatTree


class Application(Frame):
    def __init__(self, master=None):
        Frame.__init__(self, master)
        self.pack()
        self.createWidgets()

    def createWidgets(self):
        self.hi_there = Button(self)
        self.hi_there["text"] = "Hello World\n(click me)"
        self.hi_there["command"] = self.say_hi
        self.hi_there.pack(side="top")

        self.QUIT = Button(self, text="QUIT", command=root.destroy)
        self.QUIT.pack(side="bottom")

    def say_hi(self):
        print("hi there, everyone!")

def draw_rect():
    canvas_width = 200
    canvas_height = 100

    colours = ("#476042", "yellow")
    box=[]

    for ratio in ( 0.2, 0.35 ):
       box.append( (canvas_width * ratio,
                    canvas_height * ratio,
                    canvas_width * (1 - ratio),
                    canvas_height * (1 - ratio) ) )

    master = Tk()

    w = Canvas(master,
               width=canvas_width,
               height=canvas_height)
    w.pack()

    for i in range(2):
       w.create_rectangle(box[i][0], box[i][1],box[i][2],box[i][3], fill=colours[i])

    w.create_line(0, 0,                 # origin of canvas
                  box[0][0], box[0][1], # coordinates of left upper corner of the box[0]
                  fill=colours[0],
                  width=3)
    w.create_line(0, canvas_height,     # lower left corner of canvas
                  box[0][0], box[0][3], # lower left corner of box[0]
                  fill=colours[0],
                  width=3)
    w.create_line(box[0][2],box[0][1],  # right upper corner of box[0]
                  canvas_width, 0,      # right upper corner of canvas
                  fill=colours[0],
                  width=3)
    w.create_line(box[0][2], box[0][3], # lower right corner pf box[0]
                  canvas_width, canvas_height, # lower right corner of canvas
                  fill=colours[0], width=3)

    w.create_text(canvas_width / 2,
                  canvas_height / 2,
                  text="Python")

    nTextWidget(w, text="Hallöchen!")

    mainloop()

def draw_notebook():
    master = Tk()
    n = Notebook(master)
    n.pack()
    f1 = Frame(n)   # first page, which would get widgets gridded into it
    f2 = Frame(n)   # second page
    n.add(f1, text='One')
    n.add(f2, text='Two')
    mainloop()

class nTextWidget(CanvasWidget):
    """
    A canvas widget that displays some text.

    Attributes:
      - ``fill``: the color of the text.
      - ``font``: the font used to display the text.
      - ``justify``: justification for multi-line texts.  Valid values
        are ``left``, ``center``, and ``right``.
      - ``width``: the width of the text.  If the text is wider than
        this width, it will be line-wrapped at whitespace.
      - ``draggable``: whether the text can be dragged by the user.
    """
    def __init__(self, canvas, text, **attribs):
        """
        Create a new text widget.

        :type canvas: Tkinter.Canvas
        :param canvas: This canvas widget's canvas.
        :type text: str
        :param text: The string of text to display.
        :param attribs: The new canvas widget's attributes.
        """
        self._text = text
        self._tag = canvas.create_text(1, 1, text=text)
        CanvasWidget.__init__(self, canvas, **attribs)

    def __setitem__(self, attr, value):
        if attr in ('fill', 'font', 'justify', 'width'):
            self.canvas().itemconfig(self._tag, {attr:value})
        else:
            CanvasWidget.__setitem__(self, attr, value)

    def __getitem__(self, attr):
        if attr in ('fill', 'font', 'justify', 'width'):
            return self.canvas().itemcget(self._tag, attr)
        else:
            return CanvasWidget.__getitem__(self, attr)

    def _tags(self): return [self._tag]

    def text(self):
        """
        :return: The text displayed by this text widget.
        :rtype: str
        """
        return self.canvas().itemcget(self._tag, 'TEXT')

    def set_text(self, text):
        """
        Change the text that is displayed by this text widget.

        :type text: str
        :param text: The string of text to display.
        :rtype: None
        """
        self.canvas().itemconfig(self._tag, text=text)
        if self.parent() is not None:
            self.parent().update(self)

    def __repr__(self):
        return '[Text: %r]' % self._text

class nTreeSegmentWidget(CanvasWidget):
    """
    A canvas widget that displays a single segment of a hierarchical
    tree.  Each ``TreeSegmentWidget`` connects a single "node widget"
    to a sequence of zero or more "subtree widgets".  By default, the
    bottom of the node is connected to the top of each subtree by a
    single line.  However, if the ``roof`` attribute is set, then a
    single triangular "roof" will connect the node to all of its
    children.

    Attributes:
      - ``roof``: What sort of connection to draw between the node and
        its subtrees.  If ``roof`` is true, draw a single triangular
        "roof" over the subtrees.  If ``roof`` is false, draw a line
        between each subtree and the node.  Default value is false.
      - ``xspace``: The amount of horizontal space to leave between
        subtrees when managing this widget.  Default value is 10.
      - ``yspace``: The amount of space to place between the node and
        its children when managing this widget.  Default value is 15.
      - ``color``: The color of the lines connecting the node to its
        subtrees; and of the outline of the triangular roof.  Default
        value is ``'#006060'``.
      - ``fill``: The fill color for the triangular roof.  Default
        value is ``''`` (no fill).
      - ``width``: The width of the lines connecting the node to its
        subtrees; and of the outline of the triangular roof.  Default
        value is 1.
      - ``orientation``: Determines whether the tree branches downwards
        or rightwards.  Possible values are ``'horizontal'`` and
        ``'vertical'``.  The default value is ``'vertical'`` (i.e.,
        branch downwards).
      - ``draggable``: whether the widget can be dragged by the user.
    """

    def __init__(self, canvas, label, subtrees, featTree = NONE, **attribs):
        """
        :type node:
        :type subtrees: list(CanvasWidgetI)
        """
        self._label = label
        self._subtrees = subtrees

        # Attributes
        self._horizontal = 0
        self._roof = 0
        self._xspace = 5
        self._yspace = 15
        self._ordered = False
        self._featTree = featTree

        # Create canvas objects.
        self._lines = [canvas.create_line(0, 0, 0, 0, )
                       for c in subtrees]

        self._rect = canvas.create_rectangle(0,0,0,0)


        # Register child widgets (label + subtrees)
        self._add_child_widget(label)
        for subtree in subtrees:
            self._add_child_widget(subtree)

        # Are we currently managing?
        self._managing = False

        CanvasWidget.__init__(self, canvas, **attribs)

    def __setitem__(self, attr, value):
        canvas = self.canvas()
        if attr == 'roof':
            self._roof = value
            if self._roof:
                for l in self._lines: canvas.itemconfig(l, state='hidden')
                canvas.itemconfig(self._polygon, state='normal')
            else:
                for l in self._lines: canvas.itemconfig(l, state='normal')
                canvas.itemconfig(self._polygon, state='hidden')
        elif attr == 'orientation':
            if value == 'horizontal':
                self._horizontal = 1
            elif value == 'vertical':
                self._horizontal = 0
            else:
                raise ValueError('orientation must be horizontal or vertical')
        elif attr == 'color':
            for l in self._lines: canvas.itemconfig(l, fill=value)
            canvas.itemconfig(self._polygon, outline=value)
        elif isinstance(attr, tuple) and attr[0] == 'color':
            # Set the color of an individual line.
            l = self._lines[int(attr[1])]
            canvas.itemconfig(l, fill=value)
        elif attr == 'fill':
            pass
            #print("Warning! Attribute fill is not setted")
            #canvas.itemconfig(self._polygon, fill=value)
        elif attr == 'width':
            canvas.itemconfig(self._polygon, {attr: value})
            for l in self._lines: canvas.itemconfig(l, {attr: value})
        elif attr in ('xspace', 'yspace'):
            if attr == 'xspace':
                self._xspace = value
            elif attr == 'yspace':
                self._yspace = value
            self.update(self._label)
        elif attr == 'ordered':
            self._ordered = value
        else:
            CanvasWidget.__setitem__(self, attr, value)

    def __getitem__(self, attr):
        if attr == 'roof':
            return self._roof
        elif attr == 'width':
            return self.canvas().itemcget(self._polygon, attr)
        elif attr == 'color':
            return self.canvas().itemcget(self._polygon, 'outline')
        elif isinstance(attr, tuple) and attr[0] == 'color':
            l = self._lines[int(attr[1])]
            return self.canvas().itemcget(l, 'fill')
        elif attr == 'xspace':
            return self._xspace
        elif attr == 'yspace':
            return self._yspace
        elif attr == 'orientation':
            if self._horizontal:
                return 'horizontal'
            else:
                return 'vertical'
        elif attr == 'ordered':
            return self._ordered
        else:
            return CanvasWidget.__getitem__(self, attr)

    def label(self):
        return self._label

    def subtrees(self):
        return self._subtrees[:]

    def set_label(self, label):
        """
        Set the node label to ``label``.
        """
        self._remove_child_widget(self._label)
        self._add_child_widget(label)
        self._label = label
        self.update(self._label)

    def replace_child(self, oldchild, newchild):
        """
        Replace the child ``oldchild`` with ``newchild``.
        """
        index = self._subtrees.index(oldchild)
        self._subtrees[index] = newchild
        self._remove_child_widget(oldchild)
        self._add_child_widget(newchild)
        self.update(newchild)

    def remove_child(self, child):
        index = self._subtrees.index(child)
        del self._subtrees[index]
        self._remove_child_widget(child)
        self.canvas().delete(self._lines.pop())
        self.update(self._label)

    def insert_child(self, index, child):
        canvas = self.canvas()
        self._subtrees.insert(index, child)
        self._add_child_widget(child)
        self._lines.append(canvas.create_line(0, 0, 0, 0))
        self.update(self._label)

    def _tags(self):
        if self._roof:
            return [self._polygon]
        else:
            return self._lines + [self._rect,]

    def _subtree_top(self, child):
        xmin, ymin, xmax, ymax = self._subtree_bbox(child)
        if self._horizontal:
            return (xmin, (ymin + ymax) / 2.0)
        else:
            return ((xmin + xmax) / 2.0, ymin)

    def _subtree_bbox(self, child):
        if isinstance(child, nTreeSegmentWidget):
            return child.label().bbox()
        else:
            return child.bbox()

    def _node_bottom(self):
        bbox = self._label.bbox()
        if self._horizontal:
            return (bbox[2], (bbox[1] + bbox[3]) / 2.0)
        else:
            return ((bbox[0] + bbox[2]) / 2.0, bbox[3])

    def _border(self):
        for edge in self._featTree:
            if not isinstance(edge, FeatTree.FeatTree):
                return

        if self._featTree.parent:
            for topology in self._featTree.parent.topologies:
                for field in topology.keys():
                    if field.shared_from:
                        self.canvas().itemconfig(self._rect, dash=(3,5))
                        break

        xmin = ymin = sys.maxsize
        xmax = ymax = 0
        for subtree in self._subtrees:
            x1,y1,x2,y2 = self._subtree_bbox(subtree)
            if x1 < xmin:
                xmin = x1
            if y1 < ymin:
                ymin = y1
            if x2 > xmax:
                xmax = x2
            if y2 > ymax:
                ymax = y2
            # if isinstance(subtree, nTreeSegmentWidget):
            #     subtree._border()
        self.canvas().coords(self._rect, xmin, ymin, xmax, ymax)

    def _update(self, child):
        if len(self._subtrees) == 0: return
        if self._label.bbox() is None: return  # [XX] ???

        # Which lines need to be redrawn?
        if child is self._label:
            need_update = self._subtrees
        else:
            need_update = [child]

        if self._ordered and not self._managing:
            need_update = self._maintain_order(child)

        # Update the rect.
        self._border()




        # if self._horizontal:
        #     self.canvas().coords(self._rect, xmin,
        #                          ymin, xmin, ymax)
        # else:
        #     self.canvas().coords(self._rect, xmin,
        #                          ymin, xmax, ymin)

       # if self._horizontal:
       #      self.canvas().coords(self._rect, nodex, nodey, xmin,
       #                           ymin, xmin, ymax, nodex, nodey)
       #  else:
       #      self.canvas().coords(self._rect, nodex, nodey, xmin,
       #                           ymin, xmax, ymin, nodex, nodey)



        # Redraw all lines that need it.
        for subtree in need_update:
            (nodex, nodey) = self._node_bottom()
            line = self._lines[self._subtrees.index(subtree)]
            (subtreex, subtreey) = self._subtree_top(subtree)
            self.canvas().coords(line, nodex, nodey, subtreex, subtreey)

    def _maintain_order(self, child):
        if self._horizontal:
            return self._maintain_order_horizontal(child)
        else:
            return self._maintain_order_vertical(child)

    def _maintain_order_vertical(self, child):
        (left, top, right, bot) = child.bbox()

        if child is self._label:
            # Check all the leaves
            for subtree in self._subtrees:
                (x1, y1, x2, y2) = subtree.bbox()
                if bot + self._yspace > y1:
                    subtree.move(0, bot + self._yspace - y1)

            return self._subtrees
        else:
            moved = [child]
            index = self._subtrees.index(child)

            # Check leaves to our right.
            x = right + self._xspace
            for i in range(index + 1, len(self._subtrees)):
                (x1, y1, x2, y2) = self._subtrees[i].bbox()
                if x > x1:
                    self._subtrees[i].move(x - x1, 0)
                    x += x2 - x1 + self._xspace
                    moved.append(self._subtrees[i])

            # Check leaves to our left.
            x = left - self._xspace
            for i in range(index - 1, -1, -1):
                (x1, y1, x2, y2) = self._subtrees[i].bbox()
                if x < x2:
                    self._subtrees[i].move(x - x2, 0)
                    x -= x2 - x1 + self._xspace
                    moved.append(self._subtrees[i])

            # Check the node
            (x1, y1, x2, y2) = self._label.bbox()
            if y2 > top - self._yspace:
                self._label.move(0, top - self._yspace - y2)
                moved = self._subtrees

        # Return a list of the nodes we moved
        return moved

    def _maintain_order_horizontal(self, child):
        (left, top, right, bot) = child.bbox()

        if child is self._label:
            # Check all the leaves
            for subtree in self._subtrees:
                (x1, y1, x2, y2) = subtree.bbox()
                if right + self._xspace > x1:
                    subtree.move(right + self._xspace - x1)

            return self._subtrees
        else:
            moved = [child]
            index = self._subtrees.index(child)

            # Check leaves below us.
            y = bot + self._yspace
            for i in range(index + 1, len(self._subtrees)):
                (x1, y1, x2, y2) = self._subtrees[i].bbox()
                if y > y1:
                    self._subtrees[i].move(0, y - y1)
                    y += y2 - y1 + self._yspace
                    moved.append(self._subtrees[i])

            # Check leaves above us
            y = top - self._yspace
            for i in range(index - 1, -1, -1):
                (x1, y1, x2, y2) = self._subtrees[i].bbox()
                if y < y2:
                    self._subtrees[i].move(0, y - y2)
                    y -= y2 - y1 + self._yspace
                    moved.append(self._subtrees[i])

            # Check the node
            (x1, y1, x2, y2) = self._label.bbox()
            if x2 > left - self._xspace:
                self._label.move(left - self._xspace - x2, 0)
                moved = self._subtrees

        # Return a list of the nodes we moved
        return moved

    def _manage_horizontal(self):
        (nodex, nodey) = self._node_bottom()

        # Put the subtrees in a line.
        y = 20
        for subtree in self._subtrees:
            subtree_bbox = subtree.bbox()
            dx = nodex - subtree_bbox[0] + self._xspace
            dy = y - subtree_bbox[1]
            subtree.move(dx, dy)
            y += subtree_bbox[3] - subtree_bbox[1] + self._yspace

        # Find the center of their tops.
        center = 0.0
        for subtree in self._subtrees:
            center += self._subtree_top(subtree)[1]
        center /= len(self._subtrees)

        # Center the subtrees with the node.
        for subtree in self._subtrees:
            subtree.move(0, nodey - center)

    def _manage_vertical(self):
        (nodex, nodey) = self._node_bottom()

        x = 0
        center = 0.0
        for subtree in self._subtrees:
            xlefttop, ylefttop, xrightbottom, yrightbottom = subtree.bbox()
            # Find the center of their tops.
            center += x + (xrightbottom - xlefttop)/2
            x += xrightbottom - xlefttop + self._xspace

        # arithmetic mean of center
        center /= len(self._subtrees)

        x = 0
        max_subtree_height = 0
        # Center the subtrees with the node.
        # Put the subtrees in a line.
        for subtree in self._subtrees:
            xlefttop, ylefttop, xrightbottom, yrightbottom = subtree.bbox()
            dx = x - xlefttop + nodex - center
            dy = nodey - ylefttop + self._yspace
            subtree.move(dx, dy)
            x += xrightbottom - xlefttop + self._xspace
            if yrightbottom - ylefttop > max_subtree_height:
                max_subtree_height = yrightbottom - ylefttop



    def _manage(self):
        self._managing = True
        #(nodex, nodey) = self._node_bottom()
        if len(self._subtrees) == 0: return

        if self._horizontal:
            self._manage_horizontal()
        else:
            self._manage_vertical()

        # Update lines to subtrees.
        for subtree in self._subtrees:
            self._update(subtree)

        #self._border()

        self._managing = False

    def __repr__(self):
        return '[TreeSeg %s: %s]' % (self._label, self._subtrees)

#
# class Drawer():
#
#     root = Tk()
#     root.columnconfigure(0, weight=1)
#     root.rowconfigure(0, weight=1)
#
#     canvas = Canvas(root)
#     canvas.grid(column=0, row=0, sticky=(N, W, E, S))
#     canvas.bind("<Button-1>", xy)
#     canvas.bind("<B1-Motion>", addLine)
#     lastx, lasty = 0, 0
#
#     def xy(event):
#         global lastx, lasty
#         lastx, lasty = event.x, event.y
#
#     def addLine(event):
#         global lastx, lasty
#         canvas.create_line((lastx, lasty, event.x, event.y))
#         lastx, lasty = event.x, event.y
#
#     root.mainloop()
#
#     start()


if __name__ == '__main__':
    #draw_rect()
    draw_rect()
    # root = Tk()
    # app = Application(master=root)
    # app.mainloop()