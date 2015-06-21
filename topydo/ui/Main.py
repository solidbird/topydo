# Topydo - A todo.txt client written in Python.
# Copyright (C) 2015 Bram Schoenmakers <me@bramschoenmakers.nl>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import urwid
from six import u

from topydo.cli.CLIApplicationBase import CLIApplicationBase
from topydo.Commands import get_subcommand
from topydo.ui.CommandLineWidget import CommandLineWidget
from topydo.ui.ConsoleWidget import ConsoleWidget
from topydo.ui.TodoListWidget import TodoListWidget
from topydo.ui.ViewWidget import ViewWidget
from topydo.lib.Config import config
from topydo.lib.Sorter import Sorter
from topydo.lib import TodoFile
from topydo.lib import TodoList

COLUMN_WIDTH = 40

class UIApplication(CLIApplicationBase):
    def __init__(self):
        super(UIApplication, self).__init__()

        self.todofile = TodoFile.TodoFile(config().todotxt())
        self.todolist = TodoList.TodoList(self.todofile.read())

        self.columns = urwid.Columns([], dividechars=0, min_width=COLUMN_WIDTH)
        self.commandline = CommandLineWidget(u('topydo> '))

        # console widget
        self.console = ConsoleWidget()

        urwid.connect_signal(self.commandline, 'blur', self._blur_commandline)
        urwid.connect_signal(self.commandline, 'execute_command',
                             self._execute_handler)

        def hide_console():
            self._console_visible = False
        urwid.connect_signal(self.console, 'close', hide_console)

        # view widget
        self.viewwidget = ViewWidget(self.todolist)

        urwid.connect_signal(self.viewwidget, 'save', self._create_view)

        def hide_viewwidget():
            self._viewwidget_visible = False
        urwid.connect_signal(self.viewwidget, 'close', hide_viewwidget)

        self.mainwindow = urwid.Pile([
            ('weight', 1, self.columns),
            (1, urwid.Filler(self.commandline)),
        ])

        # the columns should have keyboard focus
        self._blur_commandline()

        self.mainloop = urwid.MainLoop(
            self.mainwindow,
            unhandled_input=self._handle_input,
            pop_ups=True
        )

    def _output(self, p_text):
        self._print_to_console(p_text + "\n")

    def _execute_handler(self, p_command, p_output=None):
        """
        Executes a command, given as a string.
        """
        p_output = p_output or self._output
        (subcommand, args) = get_subcommand(p_command.split())

        try:
            command = subcommand(
                args,
                self.todolist,
                p_output,
                self._output,
                self._input,
            )

            if command.execute() != False:
                self._post_execute()

        except TypeError:
            # TODO: show error message
            pass

    def _post_execute(self):
        super(UIApplication, self)._post_execute()

        for column, _ in self.columns.contents:
            column.update()

    def _blur_commandline(self):
        self.mainwindow.focus_item = 0

    def _focus_commandline(self):
        self.mainwindow.focus_item = 1

    def _focus_first_column(self):
        self.columns.focus_position = 0

    def _focus_last_column(self):
        end_pos = len(self.columns.contents) - 1
        self.columns.focus_position = end_pos

    def _focus_next_column(self):
        size = len(self.columns.contents)
        if self.columns.focus_position < size -1:
            self.columns.focus_position += 1

    def _focus_previous_column(self):
        if self.columns.focus_position > 0:
            self.columns.focus_position -= 1

    def _new_view(self):
        self.viewwidget.reset()
        self._viewwidget_visible = True

    def _edit_view(self):
        pass

    def _delete_view(self):
        try:
            focus = self.columns.focus_position
            del self.columns.contents[focus]

            if self.columns.contents:
                self.columns.focus_position = focus
            else:
                self._focus_commandline()
        except IndexError:
            # no columns
            pass

    def _handle_input(self, p_input):
        dispatch = {
            ':': self._focus_commandline,
            '0': self._focus_first_column,
            '$': self._focus_last_column,
            'left': self._focus_previous_column,
            'h': self._focus_previous_column,
            'right': self._focus_next_column,
            'l': self._focus_next_column,
            'C': self._new_view,
            'E': self._edit_view,
            'D': self._delete_view,
        }

        try:
            dispatch[p_input]()
        except KeyError:
            # the key is unknown, ignore
            pass

    def _create_view(self):
        self._add_column(self.viewwidget.view, self.viewwidget.title)
        self._viewwidget_visible = False

    def _add_column(self, p_view, p_title):
        todolist = TodoListWidget(p_view, p_title)
        no_output = lambda _: None
        urwid.connect_signal(todolist, 'execute_command',
                             lambda cmd: self._execute_handler(cmd, no_output))

        options = self.columns.options(
            width_type='given',
            width_amount=COLUMN_WIDTH,
            box_widget=True
        )

        item = (todolist, options)
        self.columns.contents.append(item)
        self.columns.focus_position = len(self.columns.contents) - 1
        self._blur_commandline()

    @property
    def _console_visible(self):
        contents = self.mainwindow.contents
        return len(contents) == 3 and isinstance(contents[2][0], ConsoleWidget)

    @_console_visible.setter
    def _console_visible(self, p_enabled):
        contents = self.mainwindow.contents

        if p_enabled == True and len(contents) == 2:
            contents.append((self.console, ('pack', None)))
            self.mainwindow.focus_position = 2
        elif p_enabled == False and self._console_visible:
            self.console.clear()
            del contents[2]

    @property
    def _viewwidget_visible(self):
        contents = self.mainwindow.contents
        return len(contents) == 3 and isinstance(contents[2][0], ViewWidget)

    @_viewwidget_visible.setter
    def _viewwidget_visible(self, p_enabled):
        contents = self.mainwindow.contents

        if p_enabled == True and len(contents) == 2:
            contents.append((self.viewwidget, ('pack', None)))
            self.mainwindow.focus_position = 2
        elif p_enabled == False and self._viewwidget_visible:
            del contents[2]

    def _print_to_console(self, p_text):
        self._console_visible = True
        self.console.print_text(p_text)

    def _input(self, p_question):
        self._print_to_console(p_question)

        # don't wait for the event loop to enter idle, there is a command
        # waiting for input right now, so already go ahead and draw the
        # question on screen.
        self.mainloop.draw_screen()

        user_input = self.mainloop.screen.get_input()
        self._console_visible = False

        return user_input[0]

    def run(self):
        view1 = self.todolist.view(Sorter(), [])
        self._add_column(view1, "View 1")

        self.mainloop.run()

if __name__ == '__main__':
    UIApplication().run()
