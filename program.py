#! /usr/bin/python

# SPDX-License-Identifier: GPL-3.0-or-later
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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Class representing a BASIC program.
This is a list of statements, ordered by
line number.

"""
import gc

from basictoken import BASICToken as Token
from basicparser import BASICParser
from flowsignal import FlowSignal
from lexer import Lexer

from scheduler import Scheluder, Condition, Task, Message
from dictfile import DictFile, DictFileSlow


class BASICData:

    def __init__(self, ram = False):
        # array of line numbers to represent data statements
        if ram:
            self.__datastmts = {}
        else:
            self.__datastmts = DictFileSlow("/basicdata.json")

        # Data pointer
        self.__next_data = 0
        self.data_values = []


    def delete(self):
        self.__datastmts.clear()
        self.__next_data = 0

    def delData(self,line_number):
        if self.__datastmts.get(line_number) != None:
            del self.__datastmts[line_number]

    def addData(self,line_number,tokenlist):
        """
        Adds the supplied token list
        to the program's DATA store. If a token list with the
        same line number already exists, this is
        replaced.

        line_number: Basic program line number of DATA statement

        """

        try:
            self.__datastmts[line_number] = tokenlist

        except TypeError as err:
            raise TypeError("Invalid line number: " + str(err))


    def getTokens(self,line_number):
        """
        returns the tokens from the program DATA statement

        line_number: Basic program line number of DATA statement

        """

        return self.__datastmts.get(line_number)

    def readData(self,read_line_number):

        if len(self.__datastmts) == 0:
            raise RuntimeError('No DATA statements available to READ ' +
                               'in line ' + str(read_line_number))

        self.data_values.clear()

        line_numbers = list(self.__datastmts.keys())
        line_numbers.sort()

        if self.__next_data == 0:
            self.__next_data = line_numbers[0]
        elif line_numbers.index(self.__next_data) < len(line_numbers)-1:
            self.__next_data = line_numbers[line_numbers.index(self.__next_data)+1]
        else:
            raise RuntimeError('No DATA statements available to READ ' +
                               'in line ' + str(read_line_number))

        tokenlist = self.__datastmts[self.__next_data]

        sign = 1
        for token in tokenlist[1:]:
            if token.category != Token.COMMA:
                #self.data_values.append(token.lexeme)

                if token.category == Token.STRING:
                    self.data_values.append(token.lexeme)
                elif token.category == Token.UNSIGNEDINT:
                    self.data_values.append(sign*int(token.lexeme))
                elif token.category == Token.UNSIGNEDFLOAT:
                    self.data_values.append(sign*eval(token.lexeme))
                elif token.category == Token.MINUS:
                    sign = -1
                #else:
                    #self.data_values.append(token.lexeme)
            else:
                sign = 1


        return self.data_values

    def restore(self,restoreLineNo):
        if restoreLineNo == 0 or restoreLineNo in self.__datastmts:

            if restoreLineNo == 0:
                self.__next_data = restoreLineNo
            else:

                line_numbers = list(self.__datastmts.keys())
                line_numbers.sort()

                indexln = line_numbers.index(restoreLineNo)

                if indexln == 0:
                    self.__next_data = 0
                else:
                    self.__next_data = line_numbers[indexln-1]
        else:
            raise RuntimeError('Attempt to RESTORE but no DATA ' +
                               'statement at line ' + str(restoreLineNo))


class Program:
    print = None

    def __init__(self, ram = False):
        # Dictionary to represent program
        # statements, keyed by line number
        #self.__program = {}
        if ram:
            self.__program = {}
        else:
            self.__program = DictFileSlow("/program.json")

        # Program counter
        self.__next_stmt = 0

        # Initialise return stack for subroutine returns
        self.__return_stack = []

        # return dictionary for loop returns
        self.__return_loop = {}

        # Setup DATA object
        self.__data = BASICData(ram = ram)
        self.__parser = BASICParser(None)
        BASICParser.print = self.print

    def __str__(self):

        program_text = ""
        line_numbers = self.line_numbers()

        for line_number in line_numbers:
            program_text += self.str_statement(line_number)

        return program_text

    def str_statement(self, line_number):
        line_text = str(line_number) + " "

        statement = self.__program[line_number]
        if statement[0].category == Token.DATA:
            statement = self.__data.getTokens(line_number)
        for token in statement:
            # Add in quotes for strings
            if token.category == Token.STRING:
                line_text += '"' + token.lexeme + '" '

            else:
                line_text += token.lexeme + " "
        line_text += "\n"
        return line_text

    def list(self, start_line=None, end_line=None):
        """Lists the program"""
        line_numbers = self.line_numbers()
        if not start_line:
            start_line = int(line_numbers[0])

        if not end_line:
            end_line = int(line_numbers[-1])

        for line_number in line_numbers:
            if int(line_number) >= start_line and int(line_number) <= end_line:
                self.print(self.str_statement(line_number), end = '')

    def save(self, file):
        """Save the program

        :param file: The name and path of the save file, .bas is
                     appended

        """
        if not file.lower().endswith(".bas"):
            file += ".bas"
        try:
            with open(file, "w") as outfile:
                outfile.write(str(self))
        except OSError:
            raise OSError("Could not save to file")

    def load(self, file):
        """Load the program

        :param file: The name and path of the file to be loaded, .bas is
                     appended

        """

        # New out the program
        self.delete()
        if not file.lower().endswith(".bas"):
            file += ".bas"
        try:
            lexer = Lexer()
            with open(file, "r") as infile:
                line = infile.readline()
                line = line.replace("\r", "").replace("\n", "").strip()
                while line:
                    tokenlist = lexer.tokenize(line)
                    self.add_stmt(tokenlist)
                    line = infile.readline()
                    line = line.replace("\r", "").replace("\n", "").strip()
                
                #for line in infile:
                #    line = line.replace("\r", "").replace("\n", "").strip()
                #    tokenlist = lexer.tokenize(line)
                #    self.add_stmt(tokenlist)

        except OSError:
            raise OSError("Could not read file")

    def add_stmt(self, tokenlist):
        """
        Adds the supplied token list
        to the program. The first token should
        be the line number. If a token list with the
        same line number already exists, this is
        replaced.

        :param tokenlist: List of BTokens representing a
        numbered program statement

        """
        if len(tokenlist) > 0:
            try:
                line_number = int(tokenlist[0].lexeme)
                if tokenlist[1].lexeme == "DATA":
                    self.__data.addData(line_number,tokenlist[1:])
                    self.__program[line_number] = [tokenlist[1],]
                else:
                    self.__program[line_number] = tokenlist[1:]

            except TypeError as err:
                raise TypeError("Invalid line number: " +
                                str(err))

    def line_numbers(self):
        """Returns a list of all the
        line numbers for the program,
        sorted

        :return: A sorted list of
        program line numbers
        """
        line_numbers = list(self.__program.keys())
        line_numbers.sort()

        return line_numbers

    def __execute(self, line_number, execute_print = None):
        """Execute the statement with the
        specified line number

        :param line_number: The line number

        :return: The FlowSignal to indicate to the program
        how to branch if necessary, None otherwise

        """
        if line_number not in self.__program.keys():
            raise RuntimeError("Line number " + line_number +
                               " does not exist")

        statement = self.__program[line_number]
        #execute_print("%s: [%s]" % (line_number, statement))

        try:
            return self.__parser.parse(statement, line_number)

        except RuntimeError as err:
            raise RuntimeError(str(err))

    def execute(self, task, name, execute_print = None, shell = None):
        """Execute the program"""
        
        BASICParser.print = execute_print
        self.__parser.__data = self.__data
        self.__parser.print = execute_print
        self.__parser.clear()
        gc.collect()
        self.__data.restore(0) # reset data pointer

        line_numbers = self.line_numbers()
        frame = shell.input_counter
        frame_previous = frame
        n = 0
        stop = False
        
        if len(line_numbers) > 0:
            # Set up an index into the ordered list
            # of line numbers that can be used for
            # sequential statement execution. The index
            # will be incremented by one, unless modified by
            # a jump
            index = 0
            self.set_next_line_number(line_numbers[index])

            # Run through the program until the
            # has line number has been reached
            while not stop:
                # execute_print("%s-%s-%s-%s" % (len(self.__program), len(self.__return_stack), len(self.__return_loop), len(self.__data.__datastmts)), end = '\n', terminated = True)
                gc.collect()
                msg = task.get_message()
                if msg:
                    if msg.content["msg"] == "Ctrl-C":
                        msg.release()
                        execute_print("Program terminated", end = '\n', terminated = True)
                        stop = True
                        # raise StopIteration
                    msg.release()
                frame = shell.input_counter
                if frame != frame_previous:
                    frame_previous = frame
                    n = 0
                    yield Condition.get().load(sleep = 0)
                elif n >= 10:
                    n = 0
                    yield Condition.get().load(sleep = 0)
                
                flowsignal = self.__execute(self.get_next_line_number(), execute_print)
                if flowsignal == "_wait":
                    shell.wait_for_input = True
                    yield Condition.get().load(sleep = 0, wait_msg = True)
                    msg = task.get_message()
                    if msg.content["msg"] == "Ctrl-C":
                        msg.release()
                        execute_print("Program terminated", end = '\n', terminated = True)
                        stop = True
                        # raise StopIteration
                    self.__parser.__input_value = msg.content["msg"]
                    msg.release()
                    flowsignal = self.__execute(self.get_next_line_number(), execute_print)
                self.__parser.last_flowsignal = flowsignal

                if flowsignal:
                    if flowsignal.ftype == FlowSignal.SIMPLE_JUMP:
                        # GOTO or conditional branch encountered
                        try:
                            index = line_numbers.index(flowsignal.ftarget)

                        except ValueError:
                            shell.run_program_id = None
                            execute_print("", end = "\n", terminated = True)
                            raise RuntimeError("Invalid line number supplied in GOTO or conditional branch: "
                                               + str(flowsignal.ftarget))

                        self.set_next_line_number(flowsignal.ftarget)

                    elif flowsignal.ftype == FlowSignal.GOSUB:
                        # Subroutine call encountered
                        # Add line number of next instruction to
                        # the return stack
                        if index + 1 < len(line_numbers):
                            self.__return_stack.append(line_numbers[index + 1])

                        else:
                            shell.run_program_id = None
                            execute_print("", end = "\n", terminated = True)
                            raise RuntimeError("GOSUB at end of program, nowhere to return")

                        # Set the index to be the subroutine start line
                        # number
                        try:
                            index = line_numbers.index(flowsignal.ftarget)

                        except ValueError:
                            shell.run_program_id = None
                            execute_print("", end = "\n", terminated = True)
                            raise RuntimeError("Invalid line number supplied in subroutine call: "
                                               + str(flowsignal.ftarget))

                        self.set_next_line_number(flowsignal.ftarget)

                    elif flowsignal.ftype == FlowSignal.RETURN:
                        # Subroutine return encountered
                        # Pop return address from the stack
                        try:
                            index = line_numbers.index(self.__return_stack.pop())

                        except ValueError:
                            shell.run_program_id = None
                            execute_print("", end = "\n", terminated = True)
                            raise RuntimeError("Invalid subroutine return in line " +
                                               str(self.get_next_line_number()))

                        except IndexError:
                            shell.run_program_id = None
                            execute_print("", end = "\n", terminated = True)
                            raise RuntimeError("RETURN encountered without corresponding " +
                                               "subroutine call in line " + str(self.get_next_line_number()))

                        self.set_next_line_number(line_numbers[index])

                    elif flowsignal.ftype == FlowSignal.STOP:
                        break

                    elif flowsignal.ftype == FlowSignal.LOOP_BEGIN:
                        # Loop start encountered
                        # Put loop line number on the stack so
                        # that it can be returned to when the loop
                        # repeats
                        self.__return_loop[flowsignal.floop_var] = line_numbers[index]

                        # Continue to the next statement in the loop
                        index = index + 1

                        if index < len(line_numbers):
                            self.set_next_line_number(line_numbers[index])

                        else:
                            # Reached end of program
                            shell.run_program_id = None
                            execute_print("", end = "\n", terminated = True)
                            raise RuntimeError("Program terminated within a loop")

                    elif flowsignal.ftype == FlowSignal.LOOP_SKIP:
                        # Loop variable has reached end value, so ignore
                        # all statements within loop and move past the corresponding
                        # NEXT statement
                        index = index + 1
                        while index < len(line_numbers):
                            msg = task.get_message()
                            if msg:
                                if msg.content["msg"] == "Ctrl-C":
                                    msg.release()
                                    execute_print("Program terminated", end = '\n', terminated = True)
                                    # raise StopIteration
                                    stop = True
                                    break
                                msg.release()
                            yield Condition.get().load(sleep = 0)
                            
                            next_line_number = line_numbers[index]
                            temp_tokenlist = self.__program[next_line_number]

                            if temp_tokenlist[0].category == Token.NEXT and \
                               len(temp_tokenlist) > 1:
                                # Check the loop variable to ensure we have not found
                                # the NEXT statement for a nested loop
                                if temp_tokenlist[1].lexeme == flowsignal.ftarget:
                                    # Move the statement after this NEXT, if there
                                    # is one
                                    index = index + 1
                                    if index < len(line_numbers):
                                        next_line_number = line_numbers[index]  # Statement after the NEXT
                                        self.set_next_line_number(next_line_number)
                                        break

                            index = index + 1

                        # Check we have not reached end of program
                        if index >= len(line_numbers):
                            # Terminate the program
                            break

                    elif flowsignal.ftype == FlowSignal.LOOP_REPEAT:
                        # Loop repeat encountered
                        # Pop the loop start address from the stack
                        try:
                            index = line_numbers.index(self.__return_loop.pop(flowsignal.floop_var))

                        except ValueError:
                            shell.run_program_id = None
                            execute_print("", end = "\n", terminated = True)
                            raise RuntimeError("Invalid loop exit in line " +
                                               str(self.get_next_line_number()))

                        except KeyError:
                            execute_print("", end = "\n", terminated = True)
                            shell.run_program_id = None
                            raise RuntimeError("NEXT encountered without corresponding " +
                                               "FOR loop in line " + str(self.get_next_line_number()))

                        self.set_next_line_number(line_numbers[index])

                else:
                    index = index + 1

                    if index < len(line_numbers):
                        self.set_next_line_number(line_numbers[index])

                    else:
                        # Reached end of program
                        break
                n += 1
                #yield Condition(sleep = 0)

        else:
            shell.run_program_id = None
            execute_print("", end = "\n", terminated = True)
            raise RuntimeError("No statements to execute")
        shell.run_program_id = None
        execute_print("", end = "\n", terminated = True)

    def delete(self):
        """Deletes the program by emptying the dictionary"""
        self.__program.clear()
        self.__data.delete()

    def delete_statement(self, line_number):
        """Deletes a statement from the program with
        the specified line number, if it exists

        :param line_number: The line number to be deleted

        """
        self.__data.delData(line_number)
        try:
            del self.__program[line_number]

        except KeyError:
            raise KeyError("Line number does not exist")

    def get_next_line_number(self):
        """Returns the line number of the next statement
        to be executed

        :return: The line number

        """

        return self.__next_stmt

    def set_next_line_number(self, line_number):
        """Sets the line number of the next
        statement to be executed

        :param line_number: The new line number

        """
        self.__next_stmt = line_number
