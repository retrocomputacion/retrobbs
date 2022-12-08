# SID Streaming Protocol:

## Host Side

1. Using *SIDDump* get a dump of SID registers used for each frame.
2. *HVSC* song length files are used to know the playtime. If no song length file is found the default is 3 minutes.
3. The dump is interpreted and a list of values to transmit is generated for each frame. Along with a corresponding bitmap defining which registers are used each frame.

4. Each frame register list is built a data packet taking this form:

|Position | Length (bytes)| Description
|:---:|:---:|---
| 1 | 1 | Length of this data packet (max 30)
| 2 | 4 | Bitmap of SID registers sent.<br>1bit = 1 register (Big endian)
| 6 onwards | 1 to 24 | Values of each register, in incremental order by default 

5. Send the packets acording to this flowchart:

```mermaid
flowchart TD
 id1([Start])
 id2(Send SID streaming command)
 id3(Set count to 100)
 id4(Send Packet)
 id5{Last Packet?}
 id6(Decrement count)
 id7{Count == 0?}
 id8(Receive client sync)
 id9{Sync == $FF?}
 id10(Send $00)
 id11(Flush receive buffer)
 id12([End])
 id1-->id2-->id3-->id4-->id5
 id5-- No -->id6-->id7
 id7-- No -->id4
 id7-- Yes -->id8-->id9
 id9-- No -->id3
 id5 & id9-- Yes -->id10-->id11-->id12

```


---
## Client side flowchart:

```mermaid
flowchart TD
    id1([Receive streaming command])
    id2(Set count to 50)
    id3(Read data packet)
    id4(Write SID registers)
    id5(Decrement count)
    id6{count == 0?}
    id7{user cancel?}
    id8(Send $00 sync)
    id9(Set count to 100)
    id10{Packet size == 0?}
    id11([End streaming])
    id12(Send $FF sync)
    id1 ---> id2 --> id3 --> id10 
    id10 -- No --> id4 --> id5 --> id6
    id10 -- Yes --------> id11
    id6 -- Yes --> id7
    id6 -- No --> id3
    id7 -- No --> id8
    id7 -- Yes --> id12
    id8 & id12 --> id9
    id9 --> id3
```