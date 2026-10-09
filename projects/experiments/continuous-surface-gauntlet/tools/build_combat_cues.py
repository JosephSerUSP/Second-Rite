"""Deterministic original placeholder combat cues. No external audio sources."""
import argparse,io,math,random,struct,wave
from pathlib import Path

def cue(kind):
    rate=22050;duration={'pulse':.13,'impact':.18,'sweep':.22}[kind];rng=random.Random(4801)
    data=[];phase=0
    for i in range(int(rate*duration)):
        t=i/rate;p=t/duration
        frequency={'pulse':950*(1-p)+130,'impact':110,'sweep':500*(1-p)+80}[kind]
        phase+=2*math.pi*frequency/rate
        noise=rng.uniform(-1,1)
        value=(.65*noise+.35*math.sin(phase)) if kind=='impact' else (.8*math.sin(phase)+.2*noise)
        envelope=min(1,t/.003)*(1-p)**3
        data.append(struct.pack('<h',int(value*envelope*.4*32767)))
    out=io.BytesIO()
    with wave.open(out,'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate);w.writeframes(b''.join(data))
    return out.getvalue()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]/'assets/audio';root.mkdir(exist_ok=True)
    for kind in ('pulse','impact','sweep'):
        path=root/(kind+'.wav');data=cue(kind)
        if args.check:assert path.read_bytes()==data,'stale cue '+kind
        else:path.write_bytes(data)
    print('COMBAT CUES OK')
if __name__=='__main__':main()
