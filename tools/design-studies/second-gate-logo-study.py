from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'tools' / 'design-studies' / 'second-gate-logo-study'
OUT.mkdir(parents=True, exist_ok=True)
# The backdrop this study previews logo candidates against.
#
# It used to be assets/title/st_maria_title_psx.png, which broke twice: #700
# moved Second Gate under projects/hichaukitoden-game/ so the repo-root path
# stopped resolving, and b68f4a9f then deleted the file outright when the title
# became a looping Effekseer animation. The title has no backdrop image any
# more -- the effect IS the title -- so the honest stand-in for "current title
# art" is the committed golden of the real title screen at its fully-resolved
# frame.
BG = ROOT / 'tools' / 'golden' / 'screens' / 'menu' / 'title' / '07-after-escape.png'
if not BG.exists():
    raise SystemExit(
        'backdrop missing: ' + str(BG) +
        ' -- this study needs a picture of the current title screen; '
        'recapture the golden screens or point BG at another image.')


W, H = 1600, 720
IVORY = (224, 216, 191, 255)
SMOKE = (174, 181, 169, 255)
GOLD = (184, 164, 119, 255)
INK = (18, 22, 25, 255)
SERIF = r'C:\Windows\Fonts\georgia.ttf'
SERIF_B = r'C:\Windows\Fonts\georgiab.ttf'
SANS = r'C:\Windows\Fonts\arial.ttf'
SANS_B = r'C:\Windows\Fonts\arialbd.ttf'

def font(path, size): return ImageFont.truetype(path, size)
def fit(draw, text, f, maxw):
    while draw.textbbox((0,0), text, font=f)[2] > maxw:
        f = font(SERIF if path_is_serif(f) else SANS, f.size-1)
    return f
def path_is_serif(f): return True
def centered(draw, text, y, f, fill, canvas=W):
    box = draw.textbbox((0,0), text, font=f, stroke_width=0)
    x = (canvas-(box[2]-box[0]))//2
    draw.text((x,y), text, font=f, fill=fill)
    return x, box[2]-box[0]
def cut_aperture(img, x, y, w, h):
    d = ImageDraw.Draw(img)
    d.rectangle((x, y, x+w, y+h), fill=(0,0,0,0))
def add_shadow(img, offset=5):
    alpha = img.getchannel('A').filter(ImageFilter.GaussianBlur(2))
    sh = Image.new('RGBA', img.size, (0,0,0,0)); sh.paste((0,0,0,150), (offset,offset), alpha)
    return Image.alpha_composite(sh, img)

def make(i):
    im = Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(im)
    if i==1: # small SECOND / dominant GATE, editorial serif
        f1=font(SERIF,96); f2=font(SERIF_B,220)
        centered(d,'SECOND',95,f1,SMOKE); centered(d,'GATE',190,f2,IVORY)
        d.line((445,530,1155,530), fill=GOLD, width=3)
    elif i==2: # equal wide wordmark, constructed sans
        f=font(SANS,120); centered(d,'SECOND GATE',230,f,IVORY)
        d.line((180,445,1420,445), fill=SMOKE, width=4)
        d.line((760,170,760,500), fill=GOLD, width=5)
    elif i==3: # compact stacked, narrow serif
        f=font(SERIF_B,145); centered(d,'SECOND',105,f,IVORY); centered(d,'GATE',315,f,IVORY)
        d.rectangle((420,294,1180,302), fill=GOLD)
        d.rectangle((760,100,768,535), fill=SMOKE)
    elif i==4: # offset alignment / severe geometric
        f=font(SANS_B,130); d.text((180,170),'SECOND',font=f,fill=SMOKE)
        d.text((510,330),'GATE',font=font(SANS_B,205),fill=IVORY)
        d.line((176,350,1345,350),fill=GOLD,width=5)
        d.line((480,150,480,545),fill=IVORY,width=2)
    elif i==5: # strange late-90s display, repeated vertical threshold
        f=font(SERIF,125); centered(d,'SECOND',115,f,SMOKE); centered(d,'GATE',285,font(SERIF_B,185),IVORY)
        for x in (520,540,560,1040,1060,1080): d.rectangle((x,90,x+5,560),fill=(196,187,158,180))
    elif i==6: # one aperture, clean equal title
        f=font(SERIF_B,125); centered(d,'SECOND GATE',245,f,IVORY)
        d.rectangle((785,210,815,470),fill=(0,0,0,0)); d.line((800,180,800,500),fill=GOLD,width=3)
    elif i==7: # high contrast editorial, SECOND tucked left
        f=font(SERIF,86); d.text((240,150),'SECOND',font=f,fill=SMOKE)
        d.text((320,235),'GATE',font=font(SERIF_B,220),fill=IVORY)
        d.arc((220,120,1380,610),180,350,fill=GOLD,width=4)
    elif i==8: # low-res informed, monospaced-ish spaced sans
        f=font(SANS_B,95); text='S E C O N D'; centered(d,text,125,f,SMOKE)
        centered(d,'G A T E',300,font(SANS_B,165),IVORY)
        d.rectangle((390,575,1210,580),fill=GOLD)
    elif i==9:
        f=font(SERIF_B,112); centered(d,'SECOND GATE',250,f,IVORY)
        d.rectangle((795,212,812,425),fill=(0,0,0,0)); d.line((804,190,804,450),fill=GOLD,width=3)
        d.line((560,470,1040,470),fill=SMOKE,width=2)
    elif i==10:
        f=font(SERIF,108); centered(d,'SECOND GATE',245,f,SMOKE)
        d.rectangle((798,225,808,405),fill=(0,0,0,0)); d.line((803,210,803,425),fill=IVORY,width=2)
        d.line((610,450,996,450),fill=GOLD,width=2)
    elif i==11:
        d.text((270,170),'SECOND',font=font(SERIF,78),fill=SMOKE)
        d.text((340,245),'GATE',font=font(SERIF_B,200),fill=IVORY)
        d.arc((265,125,1340,590),195,315,fill=GOLD,width=3)
    elif i==12:
        d.text((235,150),'SECOND',font=font(SERIF,82),fill=SMOKE)
        d.text((300,255),'GATE',font=font(SERIF_B,205),fill=IVORY)
        d.arc((210,110,1370,610),190,270,fill=GOLD,width=3)
        d.arc((210,110,1370,610),285,350,fill=GOLD,width=3)
    elif i==13:
        d.text((250,150),'SECOND',font=font(SERIF,82),fill=SMOKE)
        d.text((330,250),'GATE',font=font(SERIF_B,205),fill=IVORY)
        d.line((270,225,1220,225),fill=GOLD,width=3)
    elif i in (14,15,16,17):
        # F/G decision comparison: keep the control and vary only the A treatment.
        if i==14:
            f=font(SERIF_B,112); centered(d,'SECOND GATE',250,f,IVORY)
            d.rectangle((795,212,812,425),fill=(0,0,0,0)); d.line((804,190,804,450),fill=GOLD,width=3)
            d.line((560,470,1040,470),fill=SMOKE,width=2)
        else:
            d.text((270,170),'SECOND',font=font(SERIF,78),fill=SMOKE)
            if i==15:
                d.text((340,245),'GATE',font=font(SERIF_B,200),fill=IVORY)
            else:
                d.text((340,245),'G',font=font(SERIF_B,200),fill=IVORY)
                d.text((680,245),'TE',font=font(SERIF_B,200),fill=IVORY)
            if i==15: d.arc((265,125,1340,590),195,315,fill=GOLD,width=3)
            if i in (16,17): d.arc((265,125,1340,590),195,315,fill=GOLD,width=3)
            red=(137,48,42,255) if i==16 else (103,43,38,255)
            # Overpaint the A with a muted red version; 17 adds gate uprights.
            if i>=16:
                # A single custom gate-shaped A: two uprights, peaked lintel,
                # and an open central passage. It replaces the letter rather
                # than sitting on top of a second A.
                gate=Image.new('RGBA',(220,230),(0,0,0,0)); gd=ImageDraw.Draw(gate)
                gd.polygon([(18,220),(82,20),(138,20),(202,220),(160,220),(140,158),(78,158),(58,220)],fill=red)
                gd.rectangle((84,72,136,155),fill=(0,0,0,0))
                gd.rectangle((70,142,150,154),fill=red)
                im.alpha_composite(gate,(510,250))
            if i==17:
                d.rectangle((615,300,627,425),fill=red)
                d.rectangle((690,300,702,425),fill=red)
                d.rectangle((625,350,692,363),fill=red)
    # restrained pixel-era edge: keep clean master, preview gets nearest-neighbor reduction.
    return im

notes = [
 'A - SECOND small over dominant GATE; editorial serif; single underline tests calm authority.',
 'B - equal wide wordmark; severe sans; center threshold bar tests horizontal title-screen fit.',
 'C - compact stacked; high-contrast serif; central vertical division tests a second passage.',
 'D - offset alignment; constructed geometric sans; crossing rule tests uncanny instability without a sigil.',
 'E - stacked serif; repeated vertical marks; tests a restrained gate/threshold rhythm.',
 'F - one equal wordmark; aperture cut through center; tests whether the name carries the symbol alone.',
 'G - SECOND tucked left of oversized GATE; editorial arc; tests asymmetry and theatrical negative space.',
 'H - spaced display lettering; pixel-era rhythm; tests readability at low logical resolution.',
]

for n in range(1,9):
    master=make(n)
    master.save(OUT/f'second-gate-logo-{chr(96+n)}-master.png')
    preview=master.resize((800,360),Image.Resampling.LANCZOS)
    preview.save(OUT/f'second-gate-logo-{chr(96+n)}-preview.png')

refine_labels = {9:'f-aperture',10:'f-smoky',11:'g-threshold',12:'g-split-arc',13:'g-rule'}
for n, label in refine_labels.items():
    make(n).save(OUT/f'second-gate-logo-{label}-master.png')
    make(n).resize((800,360),Image.Resampling.LANCZOS).save(OUT/f'second-gate-logo-{label}-preview.png')

# Contact sheet: neutral field and current title art as the second practical surface.
sheet=Image.new('RGB',(1800,1320),(20,23,26)); sd=ImageDraw.Draw(sheet)
bg=Image.open(BG).convert('RGB').resize((800,750),Image.Resampling.NEAREST)
sheet.paste(bg,(960,300)); sd.text((80,40),'SECOND GATE — LOGO DESIGN STUDY',font=font(SANS_B,34),fill=(220,214,196))
sd.text((80,90),'Transparent masters / 256×240 title-screen scale tests',font=font(SANS,20),fill=(158,164,154))
for idx in range(8):
    x=70+(idx%2)*430; y=155+(idx//2)*270
    cell=Image.new('RGB',(390,230),(13,16,19)); logo=Image.open(OUT/f'second-gate-logo-{chr(97+idx)}-preview.png').resize((390,175),Image.Resampling.LANCZOS)
    cell.paste(logo,(0,20),logo); cd=ImageDraw.Draw(cell); cd.text((15,198),chr(65+idx),font=font(SANS_B,22),fill=(184,164,119))
    sheet.paste(cell,(x,y))
    # small title-screen proof at logical scale, enlarged for review
    proof=bg.crop((0,0,256,240)).resize((256,240),Image.Resampling.NEAREST)
    proof.paste(logo.resize((256,115),Image.Resampling.NEAREST),(0,28),logo.resize((256,115),Image.Resampling.NEAREST))
    sheet.paste(proof,(1000+(idx%2)*270,185+(idx//2)*270))
sheet.save(OUT/'second-gate-logo-contact-sheet.png')
refine=Image.new('RGB',(1200,900),(20,23,26)); rd=ImageDraw.Draw(refine)
rd.text((55,35),'SECOND GATE - F / G REFINEMENT PASS',font=font(SANS_B,30),fill=(220,214,196))
for j,label in enumerate(refine_labels.values()):
    logo=Image.open(OUT/f'second-gate-logo-{label}-preview.png').resize((360,162),Image.Resampling.LANCZOS)
    x=55+(j%3)*380; y=125+(j//3)*250
    refine.paste(logo,(x,y),logo); rd.text((x+10,y+178),label.upper(),font=font(SANS_B,18),fill=(184,164,119))
refine.save(OUT/'second-gate-logo-refinement-sheet.png')

decision_labels = {14:'f-control',15:'g-ivory',16:'g-red-a',17:'g-gate-a'}
for n,label in decision_labels.items():
    make(n).save(OUT/f'second-gate-logo-{label}-master.png')
    make(n).resize((800,360),Image.Resampling.LANCZOS).save(OUT/f'second-gate-logo-{label}-preview.png')
decision=Image.new('RGB',(1200,700),(20,23,26)); dd=ImageDraw.Draw(decision)
dd.text((55,35),'SECOND GATE - F / G A-TREATMENT COMPARISON',font=font(SANS_B,28),fill=(220,214,196))
for j,label in enumerate(decision_labels.values()):
    logo=Image.open(OUT/f'second-gate-logo-{label}-preview.png').resize((520,234),Image.Resampling.LANCZOS)
    x=55+(j%2)*580; y=110+(j//2)*280
    decision.paste(logo,(x,y),logo); dd.text((x+12,y+242),label.upper(),font=font(SANS_B,18),fill=(184,164,119))
decision.save(OUT/'second-gate-logo-f-g-a-treatment-sheet.png')
(OUT/'NOTES.txt').write_text('\n'.join(notes)+'\n\nMasters are transparent RGBA PNGs at 1600x720. Previews are 800x360. Contact sheet includes neutral dark field and current St. Maria title art proofs. These are design-study artifacts only; no title scene or golden reference was changed.\n',encoding='ascii')
