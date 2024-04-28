<div align = center>

![logo](tml.png)
# **Turbo Markup Language (TML)**
## A markup and scripting language for RetroBBS
##### (preliminary)
---
---

</div>

## Table of contents

1. [Introduction](#introduction)
2. [The basics](#the-basics)
3. [The internal registers](#the-internal-registers)
4. [Command reference](#command-reference)
   1. [Common control codes](#common-control-codes)
   2. [Register operations](#register-operations)
   3. [System/connection variables](#systemconnection-variables)
   4. [Input](#input)
   5. [Block instructions](#block-instructions)
   6. [Other generic instructions](#other-generic-instructions)
   7. [Turbo56k related commands](#turbo56k-related-commands)
   8. [RetroBBS core functions](#retrobbs-core-functions)
   9. [Plugin functions](#plugin-functions)
5. [Platform specific commands]()
---
---
## **Introduction**

Before the introduction of **TML** _RetroBBS_ relied in great part on hard-coding strings, control codes and special characters to match the target client platform (just the _Commodore 64_ at the time of this writing). This limited and complicated adding new target platforms.

The solution would come in the form of a language capable of describing platform specific encodings and control codes in plain text.

Taking inspiration in the markup style used to describe control codes on type-in programs published in 80s magazines, we have developed a new markup and scripting language based on _HTML_ syntax.

In addition to help describe control codes and _Turbo56K_ commands, __TML__ also supports a limited _'register'_ set which when used with some basic statements for flow control allows for the creation of loops and conditional execution.

A subset of _RetroBBS_ internal functions are also available, as well as every installed plugin.

---
---
## **The basics**

**TML** syntax is based on _HTML_ and is in fact parsed using a child class to Python's HTMLParser

_Tags_ are the functions or statements in this language, a basic statement can output a single or multiple copies of the corresponding character or control code. Functions can have a more complex output, or alter the state of the BBS or client. Tags are always written in **UPPERCASE**

##### Example: clear screen and output a checkmark character
```html
<CLR><CHECKMARK>
```
Almost all tags have optional parameters, this take the format `parameter=value`, if a parameter is not passed the default value will be used. Parameter names are always **lowercase**, with a few exceptions.

##### Example: Output 20 white Pi characters, wait 2 seconds, output a newline and 5 yellow Pound characters
```html
<WHITE><PI n=20>
<PAUSE n=2>
<BR>
<YELLOW><POUND n=5>
```


Block tags include conditional execution and loop statements, and contrary to other tags, need a matching closing tag.

##### Example: Clear screen, then move the cursor and sound the client's BELL _only_ if the client understand C64 PETSCII. Then output the character code 200.
```html
<CLR>
<MODE m=PET64>
    <AT x=5 y=20>
    <BELL>
</MODE>
<CHR c=200>
```
Plain text in between tags is automatically encoded to the target client, newline and tab characters are stripped out before the script is interpreted.

##### Example: A red 'Hello' and a green ' World!' will be printed on the same line on the client's screen
```html
<RED>HELLO
    <GREEN>
 WORLD!
```
Use HTML entities `&lt;` and `&gt;` to output `<` and `>` respectively, use the break tag `<BR>` to insert line breaks.

If you need to escape a control code in a string parameter, instead of using the normal _Python_ forward slash (`/`) use HTML entity numbers, for example: `/r` must be represented by `&#13;`.

---
---
## **The internal registers**
To make possible the execution of loops, conditional and other data manipulation, a small set of _'registers'_ are available:

#### **_R Return register**:
Read only register, this register will contain the result from the last function call.
</br>When used as a parameter, indicates to which register the result will be redirected/assigned to.

##### Example: assign _'hello'_ to **_S**, notice the reversed notation
```html
<LET _R=_S x='hello'>
```

#### **_C Connection register**:
When written to, any character or string input will be sent to the client.
Reading this register returns the current connection object.

#### **_B Binary connection register**:
Write only register, this register accepts binary values or strings to be sent to the client

#### **_A Accumulator**:
General purpose register, values stored into, or read from this register will not be typecast.

#### **_S String accumulator**:
String register, any value stored into this register will be typecast to a Python `str`.</br>If the typecasting fails `_S` will be `''`.

#### **_I Integer accumulator**:
Integer register, any value stored into this register will be typecast to a Python `int`.</br>If the typecasting fails `_I` will be `0`.

#### **Registers, parameter values and expressions**:
The internal registers can be passed as parameters and can be used in any expression that's accepted by _Python's_ `eval()` function.

##### Example: Output the string *'_I = 2'* to the client's screen.
```html
<LET _R=_I x=2>
<LET _R=_S x='_I = '>
<OUT x='_S+str(_I)'>
```
Note the use of quotes in the parameter values, sometimes it will be needed to nest single and double quotes:

```html
<RND e=10>
<OUT x='"Random number:"+str(_I)'>
```
---
---
## **Command reference**:


### **Common control codes**
These control code commands are common to every target platform, the connection encoder makes the corresponding conversion to the actual control codes.

</br>

#### **&lt;BELL&gt;** BELL
Send a BELL character, cause an aural or visual chime.

---
#### **&lt;CLR&gt;** Clear screen
Clears the text screen.

---
#### **&lt;HOME&gt;** Cursor home
Move the text cursor to the top left of the screen.

---
#### **&lt;CRSRL&gt;** Cursor left
#### **&lt;CRSRR&gt;** Cursor right
#### **&lt;CRSRU&gt;** Cursor up
#### **&lt;CRSRD&gt;** Cursor down
Move the text cursor in the corresponding direction.</br>
Parameter:

`n`: number of repeats, default `1` 

---
#### **&lt;DEL&gt;** Delete
Print a delete/backspace character.</br>
Parameter:

`n`: number of repeats, default `1` 

---
#### **&lt;SPC&gt;** Space
Print a space character.</br>
Parameter:

`n`: number of repeats, default `1`

---
#### **&lt;NUL&gt;** Null
Send a Null character, usually '0' (zero).</br>
Parameter:

`n`: number of repeats, default `1` 

#### **&lt;INK&gt;**
Change the text color to the value passed as parameter. Actual color is platform dependent.</br>

`c`: Index in the palette of the desired color. Default `0`.

---
</br>

### **Register operations**:
Basic instructions to assign or modify the internal registers.

</br>

#### **&lt;LET&gt;**
Assign a value to one of the internal registers.</br>
Parameters:

`_R`: Destination register, default `_I`</br>
`x`: value to assign, default `_I`

---
#### **&lt;INC&gt;**
Increment the **_I** register.

---
#### **&lt;DEC&gt;**
Decrement the **_I** register.

---
#### **&lt;RND&gt;**
Return a random integer within the selected limits in **_I**.</br>
Parameters:

`s`: lower bound of the random number range, default `0`
`e`: upper bound of the random number range, default `10`

---
#### **&lt;OUT&gt;**
Convert the input parameter to a string (if necessary) and send it to the client in the correct encoding.</br>
Parameter:

`x`: value to output, default `_I`

---
#### **&lt;LEN&gt;**
Assign the length of the input parameter to **_I**<br>
Parameter:

`x`: String or register, default `_S`
---
</br>

### **System/Connection variables**:

</br>

#### **&lt;USER&gt;**
Return the username of the current connection in **_S**

---
</br>

### **Input**:

</br>

#### **&lt;INKEYS&gt;**
Wait for the user to press a key from the list passed as parameter. Return as _byte_ in **_A**</br>
Parameter:

`k`: a string containing the valid key presses in the native client encoding, default `'/r'`

---

</br>

### **Block instructions**:
These instructions need a corresponding closing tag.
</br>

#### **&lt;IF&gt;**
Execute the code inside the block if the condition is fulfilled.</br>
Parameter:

`c`: Condition to be fulfilled, default `False`

---
#### **&lt;MODE&gt;**
Only parse the code inside this block if the connection encoding matches the **m** parameter.</br>
Parameter:

`m`: Encoding for this code block, default `'PET64'`

---
#### **&lt;SWITCH&gt;**...**&lt;CASE&gt;**
Test the expression passed as parameter for _&lt;SWITCH&gt;_ and execute the _&lt;CASE&gt;_ block matching the result.<br>
_&lt;SWITCH&gt;_ parameter:

`r`: expression to test, default `_A`

_&lt;CASE&gt;_ parameter:

`c`: value to match, default `False`

Example:

##### Wait for the user to press either the '1' or '2' keys and then spell out which one was pressed
```html
<INKEYS k='12'>
<SWITCH r=_A[0]>
    <CASE c=49>
        ONE
    </CASE>
    <CASE c=50>
        TWO
    </CASE>
</SWITCH>
```
---
#### **&lt;WHILE&gt;**
Repeat the code inside the block as long as the condition is fulfilled.<br>
Parameter:

`c`: Condition to be fulfilled, default `False`

Example:

##### Output 'LOOP!' five times
```html
<LET x=0>
<WHILE c='_I<5'>
    LOOP!
    <INC>
</WHILE>
```
---

</br>

### **Other generic instructions**:

</br>

#### **&lt;PAUSE&gt;**
Pause the execution.</br>
Parameter:

`n`: Seconds to pause (float), default `0`

---

</br>

### **Turbo56K related commands**:
</br>

#### **&lt;AT&gt;**
Move the client's text cursor to the requested position.</br>
Parameters:

`x`: Screen column. Default `0`</br>
`y`: Screen row. Default `0`

---
#### **&lt;CURSOR&gt;**
Enable or disable the client's text cursor.</br>
Parameter:

`enable`: Set to `True` to enable the text cursor. Default `True` 

---
#### **&lt;GRAPHIC&gt;**
Switch the client's screen to a graphic mode. And select the screen colors.</br>
Parameters:

`mode`: Graphic mode, True for multicolor, False for hires. Default `False`</br>
`page`: Text page number, currently unused. Default `0`</br>
`border`: Screen border color. Default `0`</br>
`background`: Screen background color. Default `0`

---
#### **&lt;LFILL&gt;**
Fill a screen row with the given character code.</br>
Parameters:

`row`: Screen row to fill. Default `0`<br>
`code`: Character code to use. Default `0`. For C64 this is a screen code, not PETSCII`

---
#### **&lt;RESET&gt;**
Reset the client's terminal screen to the default state.

---
#### **&lt;SCROLL&gt;**
Scroll the client's text screen in the required amount and direction.</br>
Parameter:

`rows`: Ammount of rows to scroll. Positive number will scroll up, negative will scroll down. Default `0`

---
#### **&lt;SETOUTPUT&gt;**
Select the client's output device.</br>
Parameter:

`o`: Boolean, True for screen, False for voice synthesizer. Default `True`

---
#### **&lt;SPLIT&gt;**
Split the client's screen in a top graphic mode section, and a bottom text mode section.</br>
Parameters:

`row`: Screen row at witch the split occurs. Default `0`</br>
`multi`: Boolean, `True` for multicolor graphic mode. Default `False`</br>
`bgtop`: Background color for the top section. Default `0`</br>
`bgbottom`: Background color for the bottom section. Default `0`

---
#### **&lt;TEXT&gt;**
Switch the client's screen to text mode. And select the screen colors.</br>
Parameters:

`page`: Text page number, currently unused. Default `0`</br>
`border`: Screen border color. Default `0`</br>
`background`: Screen background color. Default `0`

---
#### **&lt;WINDOW&gt;**
Define text window on the client screen.</br>
Parameters:

`top`: Top most row of the window. Default `0`</br>
`bottom`: Bottom most row of the window. Default `24`

---
</br>

### **RetroBBS core functions**:
</br>

#### **&lt;UNREAD&gt;**
Returns in **_A** a two-element list with the number of unread public and private messages respectively.

---
#### **&lt;MTITLE&gt;**
Render a menu title frame at the top of the client's text window.</br>
Parameters:

`t`: Title string. Default `''`

---
#### **&lt;KPROMPT&gt;**
Render a key prompt in the `[KEY]` style.</br>
Parameter:

`t`: Prompt string. Default `'RETURN'`

---
#### **&lt;DIALOG&gt;**
Render the file dialog background</br>
Parameters:

`h`: Height of the dialog box in screen rows. Default `4`</br>
`t`: Title string. Default `''`

---
#### **&lt;CAT&gt;**
Return a Python list in **_A** with the files (and subdirectories) in the directory passed as argument.</br>
Parameters:

`path`: Path to the directory to list. Default `'.'`</br>
`d`: Boolean, list subdirectories. Default `False`</br>
`f`: Boolean, add the full path to each filename/subdirectory. Default `True`

---
#### **&lt;SENDRAW&gt;**
Send a file to the client, no processing done.</br>
Parameter:

`file`: Path to the file to be sent. Default `''`

---
#### **&lt;SENDFILE&gt;**
Send a file to the client. The corresponding action or processing needed for the file type will be taken automatically.</br>
Parameters:

`file`: Path to the file to be sent. Default `''`</br>
`dialog`: Boolean, set to `True` to display the file dialog prompting user action. Default `False`</br>
`save`: Set to `True` if you want the (option for the) file to be saved to disk, as long as the file type and the client's terminal supports it. Default `False`

---
#### **&lt;GRABFRAME&gt;**
Grab a frame from a video file/stream and display it as a graphic screen on the client's terminal.

---
</br>

### **Plugin functions**:

</br>

All plugins installed are available as functions inside _TML_, the function names and parameters remain the same used in the configuration file.</br>
Refer to the plugin section in the main readme for more information.

##### Example: Play SlayRadio's Shoutcast audio stream
```html
<WEBAUDIO url='http://relay3.slayradio.org:8000/'>
```

## **Platform specific commands and tags**:

### **Commodore 64**:

#### **Color control codes**
Changes the text color to the specified color
 - **&lt;BLACK&gt;**
 - **&lt;WHITE&gt;**
 - **&lt;RED&gt;**
 - **&lt;CYAN&gt;**
 - **&lt;PURPLE&gt;**
 - **&lt;GREEN&gt;**
 - **&lt;BLUE&gt;**
 - **&lt;YELLOW&gt;**
 - **&lt;ORANGE&gt;**
 - **&lt;BROWN&gt;**
 - **&lt;PINK&gt;**
 - **&lt;GREY1&gt;** or **&lt;DGREY&gt;**
 - **&lt;GREY2&gt;** or **&lt;GREY&gt;** or **&lt;MGREY&gt;**
 - **&lt;LTGREEN&gt;**
 - **&lt;LTBLUE&gt;**
 - **&lt;GREY3&gt;** or **&lt;LT_GREY&gt;**

---

#### **&lt;RVSON&gt;**
Engage reverse video mode. Mode is automatically disengaged when a carriage return character is parsed on the terminal side

---

#### **&lt;RVSOFF&gt;**
Disengage reverse video mode.

---

#### **&lt;CBMSHIFT-D&gt;**
Disable the manual change of character sets (CBM+SHIFT key combination)

---

#### **&lt;CBMSHIFT-E&gt;**
Enable the manual change of character sets (CBM+SHIFT key combination)

---

#### **&lt;UPPER&gt;**
Change the character set to Uppercase/Graphics

---

#### **&lt;LOWER&gt;**
Change the character set to Uppercase/Lowercase

---

#### **&lt;POUND&gt;**
Displays the pound "`£`" character.

---

#### **&lt;PI&gt;**
Displays the pi "`π`" character.

---

#### **&lt;HASH&gt;**
Displays a full checkerboard character

---

#### **&lt;LEFT-HASH&gt;**
Displays a left half checkerboard character

---

#### **&lt;BOTTOM-HASH&gt;**
Displays a bottom half checkerboard character

---

#### **&lt;HLINE&gt;**
Displays a full width centered horizontal line character

---

#### **&lt;VLINE&gt;**
Displays a full height centered vertical line character

---

#### **&lt;CROSS&gt;**
Displays a full size cross character

---

#### **&lt;CHECKMARK&gt;**
Displays a checkmark "`✓`" character

---

#### **&lt;UARROW&gt;**
Displays the PETSCII upper arrow "`↑`" character, equivalent to the ASCII caret "`^`".

---

#### **&lt;LARROW&gt;**
Displays the PETSCII left arrow "`←`" character.

---

#### **&lt;CBM-U&gt;**
Displays the 3/8 upper block character.

---

#### **&lt;CBM-O&gt;**
Displays the 3/8 lower block "`▃`" character.

---

#### **&lt;CBM-B&gt;**
Displays the quadrant upper left and lower right character "`▚`"

---

#### **&lt;CBM-J&gt;**
Displays the 3/8 left block character.

---

#### **&lt;CBM-L&gt;**
Displays the 3/8 right block character.

---

</br>

### **Commodore Plus/4**:

In addition to the *Commodore 64* tags...

#### **&lt;FLASHON&gt;**
Engage character flash mode. Mode is automatically disengaged when a carriage return character is parsed on the terminal side

---

#### **&lt;FLASHOFF&gt;**
Disengage character flash mode.

---
</br>

### **MSX**:

#### **Color control codes**
Changes the text ink color to the specified color
 - **&lt;BLACK&gt;**
 - **&lt;WHITE&gt;**
 - **&lt;RED&gt;**
 - **&lt;CYAN&gt;**
 - **&lt;PURPLE&gt;**
 - **&lt;GREEN&gt;**
 - **&lt;BLUE&gt;**
 - **&lt;YELLOW&gt;**
 - **&lt;PINK&gt;**
 - **&lt;GREY&gt;**
 - **&lt;LTGREEN&gt;**
 - **&lt;LTBLUE&gt;**
 - **&lt;DRED&gt;**
 - **&lt;DGREEN&gt;**
 - **&lt;LTYELLOW&gt;**

 ---
#### **&lt;PAPER&gt;**
Changes the text paper color to the expecified color. Paper color applies only for text printed after this tag</br>
Parameters:

`c`: Palette color number, default `1` (black)</br>
