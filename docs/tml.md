<div align = center>

# Turbo Markup Language (TML)
## A markup and scripting language for RetroBBS
#### (preliminary)
---
---

</div>

## Introduction

Before the introduction of **TML** _RetroBBS_ relied in great part on hardcoding strings, control codes and special characters to match the target client platform (just the _Commodore 64_ at the time of this writing). This limited and complicated adding new target platforms.

The solution would come in the form of a language capable of describing platform specific encodings and control codes in plain text.

Taking inspiration in the markup style used to describe control codes on type-in programs published in 80's magazines, we have developed a new markup and scripting language based on _HTML_ syntax.

In addition to help describe control codes and _Turbo56K_ commands, __TML__ also supports a limited _'register'_ set which when used with some basic statements for flow control allows for the creation of loops and conditional execution.

A subset of _RetroBBS_ internal functions are also available, aswell as every installed plugin.

---
## The basics

**TML** syntax is based on _HTML_ and is in fact parsed using a child class to Python's HTMLParser

_Tags_ are the functions or statements in this language, a basic statement can output a single or multiple copies of the corresponding character or control code. Functions can have a more complex output, or alter the state of the BBS or client. Tags are always written in **UPPERCASE**

##### Example: clear screen and output a checkmark character
```html
<CLR><CHECKMARK>
```
Almost all tags have optional parameters, this take the format `parameter=value`, if a parameter is not passed the default value will be used. Parameter names are almost always lowercase.

##### Example: Output 20 white Pi characters, wait 2 seconds, output a newline and 5 yellow Pound characters
```html
<WHITE><PI n=20>
<PAUSE n=2>
<BR>
<YELLOW><POUND n=5>
```


Block tags include conditional execution and loop statements, and contrary to other tags, need a matching closing tag.

##### Example: Clear screen, move the cursor and sound the client's BELL _only_ if the client understand C64 PETSCII. Then output the character code 200.
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
 WORLD
```

