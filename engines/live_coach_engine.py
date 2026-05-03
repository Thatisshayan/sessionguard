"""
engines/live_coach_engine.py - Professional Live Coach v2.0
Fires every 3 spins. 8 pattern detectors. Claude AI + rule fallback.
"""
from __future__ import annotations
import json, os, time
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class CoachMessage:
    type: str; message: str; trigger: str; source: str; timestamp: float = 0.0
    def __post_init__(self):
        if not self.timestamp: self.timestamp = time.time()
    def to_dict(self): return asdict(self)


def _safe(v, d=0.0):
    try: return float(v) if v is not None else d
    except: return d


def _analyse_events(events):
    if not events: return {}
    nets  = [_safe(e.get('payload',{}).get('net_delta',0)) for e in events]
    bets  = [_safe(e.get('payload',{}).get('bet_amount', abs(_safe(e.get('payload',{}).get('net_delta',0))))) for e in events]
    confs = [_safe(e.get('payload',{}).get('ocr_confidence',1.0),1.0) for e in events]
    risks = [bool(e.get('payload',{}).get('risk_flag')) for e in events]
    def neg_run(ns):
        c=0
        for n in reversed(ns):
            if n<0: c+=1
            else: break
        return c
    def pos_run(ns):
        c=0
        for n in reversed(ns):
            if n>0: c+=1
            else: break
        return c
    ea = sum(bets[:max(1,len(bets)//4)])/max(1,len(bets)//4)
    la = sum(bets[-max(1,len(bets)//4):])/max(1,len(bets)//4)
    bet_changes = [bets[i]-bets[i-1] for i in range(1,len(bets))] if len(bets)>1 else []
    inc = sum(1 for c in bet_changes if c>0)
    dec = sum(1 for c in bet_changes if c<0)
    session_style = ('aggressive' if la>ea*1.5 else 'conservative' if la<ea*0.7
                     else 'inconsistent' if inc>dec*1.5 else 'disciplined')
    return {
        'event_count':len(events),'cumulative_net':round(sum(nets),2),
        'recent_net_5':round(sum(nets[-5:]),2) if len(nets)>=5 else round(sum(nets),2),
        'recent_net_10':round(sum(nets[-10:]),2) if len(nets)>=10 else round(sum(nets),2),
        'avg_bet':round(sum(bets)/len(bets),2) if bets else 0,
        'early_avg_bet':round(ea,2),'late_avg_bet':round(la,2),
        'risk_flags':sum(risks),'avg_confidence':round(sum(confs)/len(confs),2) if confs else 1.0,
        'consecutive_neg':neg_run(nets),'consecutive_pos':pos_run(nets),
        'win_rate':round(sum(1 for n in nets if n>0)/len(nets)*100,1) if nets else 0,
        'biggest_single_loss':round(min(nets),2) if nets else 0,
        'session_style':session_style,
    }


def _detect_patterns(stats, style):
    neg=stats['consecutive_neg']; pos=stats['consecutive_pos']
    cum=stats['cumulative_net']
    ea=max(stats['early_avg_bet'],0.01); la=stats['late_avg_bet']
    bet_ratio=la/ea
    def m(c,w,p): return {'strict':c,'balanced':w,'supportive':p}.get(style,w)

    if neg>=10 and bet_ratio>=2.0:
        return CoachMessage('critical',m(
            f"STOP. {neg} losses + bets {bet_ratio:.1f}x bigger. Rage spiral. Walk away.",
            f"{neg} straight losses AND bets {bet_ratio:.1f}x bigger. Classic tilt. Reset bet size now.",
            f"I know it feels like a win is due, but {neg} losses + bigger bets is how sessions spiral. Breathe first."),
            'rage_spiral','rule')
    if neg>=15:
        return CoachMessage('critical',m(
            "15 losses in a row. Stop the session.",
            "15 straight losses. Statistically deep. Consider a break.",
            "15 spins without a win. Long cold run. Stopping now protects you."),
            'critical_streak','rule')
    if bet_ratio>=2.5 and stats['event_count']>=10:
        return CoachMessage('critical',m(
            f"Bets {bet_ratio:.1f}x start. Tilt confirmed. Reset now.",
            f"Bets are {bet_ratio:.1f}x your starting size. That's tilt, not strategy.",
            f"Bets have grown to {bet_ratio:.1f}x start. Easy to miss. Bring them back."),
            'tilt_betting','rule')
    if stats['event_count']>=10 and stats['recent_net_5']<stats['recent_net_10']*0.7:
        return CoachMessage('warning',m(
            "Losses accelerating. Reduce bet size.",
            f"Last 5 spins (${stats['recent_net_5']:.0f}) worse than trend. Pace deteriorating.",
            f"Recent spins going worse than earlier. Slow down."),
            'accelerating','rule')
    if neg>=8:
        return CoachMessage('warning',m(
            f"8-loss run. Reduce stakes now.",
            f"{neg} straight losses. Normal variance — but slow down.",
            f"Tough {neg}-spin run. Stay steady, keep bets consistent."),
            'losing_streak','rule')
    if 1.4<=bet_ratio<2.5 and stats['event_count']>=8:
        return CoachMessage('warning',m(
            f"Bets up {bet_ratio:.1f}x. Pull them back.",
            f"Bet size crept up {bet_ratio:.1f}x. Worth noticing.",
            f"Bets quietly growing ({bet_ratio:.1f}x). Easy to miss."),
            'bet_creep','rule')
    if cum<=-150:
        return CoachMessage('warning',m(
            f"Down ${abs(cum):.0f}. Hard stop territory.",
            f"${abs(cum):.0f} total loss. Is this within your planned budget?",
            f"${abs(cum):.0f} down. Just checking — still within what you set aside?"),
            'budget','rule')
    if pos>=4:
        return CoachMessage('positive',m(
            f"{pos} wins. Bank some now.",
            f"{pos} wins in a row. Stay disciplined.",
            f"{pos} straight wins! Keep bets steady to lock it in."),
            'hot_streak','rule')
    n=stats['event_count']
    if n>0 and n%20==0:
        wr=stats['win_rate']; ss=stats['session_style']
        return CoachMessage('neutral',m(
            f"{n}-spin check: {wr:.0f}% wins, {ss} style. Hold discipline.",
            f"{n} spins: {wr:.0f}% wins, ${cum:.0f} net, playing {ss}.",
            f"{n} spins in. Win rate {wr:.0f}%, net {'+' if cum>=0 else ''}{cum:.0f}. Still enjoying it?"),
            'checkin','rule')
    return None


COACH_SYSTEM = """You are a professional gambling session coach — like the best boxing corner man.
Direct, calm, data-driven. 1-2 sentences MAX. Every word earns its place.
Never predict outcomes. DO call out tilt, escalation, patterns, discipline breaks.
Use the actual numbers. Match the coaching style exactly."""


def _api_key():
    k=os.getenv('ANTHROPIC_API_KEY','')
    if k: return k
    try:
        from pathlib import Path
        cfg=json.loads((Path(__file__).resolve().parent.parent/'config'/'app_config.json').read_text())
        return cfg.get('ai',{}).get('anthropic_api_key','')
    except: return ''


def _claude_coach(stats, style):
    key=_api_key()
    if not key: return None
    try:
        import anthropic
        c=anthropic.Anthropic(api_key=key)
        r=c.messages.create(model='claude-sonnet-4-20250514',max_tokens=80,
            system=COACH_SYSTEM,
            messages=[{'role':'user','content':
                f"Session: {stats['event_count']} spins, net=${stats['cumulative_net']}, "
                f"losing_run={stats['consecutive_neg']}, win_rate={stats['win_rate']}%, "
                f"bet_ratio={round(stats['late_avg_bet']/max(stats['early_avg_bet'],0.01),1)}x, "
                f"style={stats['session_style']}, coach_style={style}. "
                f"One message. 1-2 sentences. Specific."}])
        text=r.content[0].text.strip() if r.content else None
        if not text: return None
        t=('critical' if any(w in text.lower() for w in ['stop','danger','critical'])
           else 'warning' if any(w in text.lower() for w in ['careful','tilt','escalat','watch','reduce'])
           else 'positive' if any(w in text.lower() for w in ['good','great','nice','solid'])
           else 'neutral')
        return CoachMessage(t,text,'claude','claude')
    except Exception as e:
        print(f'[Coach] {e}'); return None


_last_n=0; _log=[]
FIRE_EVERY=3


def get_coaching_message(events, style='balanced', force=False):
    global _last_n, _log
    if not events: return None
    new_n=len(events)-_last_n
    if not force and new_n<FIRE_EVERY: return None
    stats=_analyse_events(events)
    _last_n=len(events)
    has_issue=(stats['consecutive_neg']>=5 or
               stats['late_avg_bet']>stats['early_avg_bet']*1.3 or
               stats['cumulative_net']<=-50 or
               stats['session_style'] in ('aggressive','inconsistent'))
    msg=None
    if has_issue: msg=_claude_coach(stats,style)
    if not msg:   msg=_detect_patterns(stats,style)
    if msg:
        d=msg.to_dict(); _log.append(d); return d
    return None


def reset_coach():
    global _last_n, _log
    _last_n=0; _log=[]


def get_session_coaching_log():
    return _log.copy()
