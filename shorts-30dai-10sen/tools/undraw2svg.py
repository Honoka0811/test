"""Textually convert react-undraw-illustrations component files to SVG (no JS executed)."""
import re, sys, os, html
KEEP_CAMEL = {'viewBox','preserveAspectRatio','gradientUnits','gradientTransform','patternUnits','spreadMethod','markerWidth','markerHeight','refX','refY','clipPathUnits','maskUnits','maskContentUnits','baseFrequency','numOctaves','stdDeviation','tableValues','filterUnits','primitiveUnits','xChannelSelector','yChannelSelector','startOffset','textLength','lengthAdjust','pathLength','attributeName','repeatCount','keyTimes','keySplines','calcMode','diffuseConstant','specularConstant','specularExponent','surfaceScale','kernelMatrix','kernelUnitLength','targetX','targetY','edgeMode','limitingConeAngle','pointsAtX','pointsAtY','pointsAtZ','zoomAndPan','systemLanguage','requiredFeatures','requiredExtensions','contentScriptType','contentStyleType','externalResourcesRequired','glyphRef','viewTarget'}
def attr_name(k):
    if k == 'className': return 'class'
    if k == 'xmlnsXlink': return 'xmlns:xlink'
    if k == 'xlinkHref': return 'xlink:href'
    if k == 'dataName': return 'data-name'
    if k in KEEP_CAMEL: return k
    return re.sub(r'([A-Z])', lambda m: '-' + m.group(1).lower(), k)

class P:
    def __init__(s, src, color): s.src=src; s.i=0; s.color=color
    def ws(s):
        while s.i < len(s.src) and s.src[s.i] in ' \t\r\n,': s.i+=1
    def peek(s, t): return s.src.startswith(t, s.i)
    def string(s):
        q=s.src[s.i]; s.i+=1; out=[]
        while s.src[s.i]!=q:
            c=s.src[s.i]
            if c=='\\': s.i+=1; c=s.src[s.i]; c={'n':'\n','t':'\t'}.get(c,c)
            out.append(c); s.i+=1
        s.i+=1; return ''.join(out)
    def value(s):
        s.ws(); c=s.src[s.i]
        if c in '\'"': return s.string()
        if c=='{': return s.obj()
        if c=='[':
            s.i+=1; items=[]
            while True:
                s.ws()
                if s.src[s.i]==']': s.i+=1; break
                items.append(s.value())
            return items
        m=re.match(r'[-+]?\d*\.?\d+(?:e[-+]?\d+)?', s.src[s.i:])
        if m and m.group(0): s.i+=len(m.group(0)); return m.group(0)
        m=re.match(r'[A-Za-z_$][\w$.]*', s.src[s.i:]); s.i+=len(m.group(0)); ident=m.group(0)
        if ident=='props.primaryColor': return s.color
        if ident=='props.height': return None
        if ident=='props.class': return None
        if ident in ('true','false','null','undefined'): return ident
        return None
    def obj(s):
        assert s.src[s.i]=='{'; s.i+=1; d={}
        while True:
            s.ws()
            if s.src[s.i]=='}': s.i+=1; return d
            if s.src[s.i] in '\'"': k=s.string()
            else:
                m=re.match(r'[A-Za-z_$][\w$]*', s.src[s.i:]); k=m.group(0); s.i+=len(k)
            s.ws(); assert s.src[s.i]==':'; s.i+=1
            d[k]=s.value()
    def element(s):
        s.ws(); assert s.peek('_react2.default.createElement('), s.src[s.i:s.i+60]
        s.i+=len('_react2.default.createElement('); s.ws()
        tag=s.string(); s.ws(); props=s.value() if s.src[s.i]=='{' else (s.i.__add__(4), {})[1]
        if props is None or not isinstance(props, dict):
            if s.src.startswith('null', s.i): s.i+=4
            props={}
        children=[]
        while True:
            s.ws()
            if s.src[s.i]==')': s.i+=1; break
            if s.peek('_react2.default.createElement('): children.append(s.element())
            elif s.src[s.i] in '\'"': children.append(html.escape(s.string()))
            else:
                v=s.value(); children.append('' if v is None else html.escape(str(v)))
        attrs=[]
        for k,v in props.items():
            if k=='style' or k=='key' or v is None: continue
            if isinstance(v,(dict,list)): continue
            attrs.append(f'{attr_name(k)}="{html.escape(str(v), quote=True)}"')
        if tag=='svg':
            if not any(a.startswith('xmlns=') for a in attrs): attrs.append('xmlns="http://www.w3.org/2000/svg"')
            if not any(a.startswith('xmlns:xlink=') for a in attrs): attrs.append('xmlns:xlink="http://www.w3.org/1999/xlink"')
        inner=''.join(children)
        return f'<{tag} {" ".join(attrs)}>{inner}</{tag}>' if inner or tag in ('svg','g','defs') else f'<{tag} {" ".join(attrs)}/>'

def convert(path, color):
    src=open(path, encoding='utf-8').read()
    i=src.index('return _react2.default.createElement(')+len('return ')
    p=P(src, color); p.i=i
    return p.element()

if __name__=='__main__':
    libdir, outdir = sys.argv[1], sys.argv[2]
    for spec in sys.argv[3:]:
        name, _, color = spec.partition(':')
        svg=convert(os.path.join(libdir,'components',name,name+'.js'), color or '#6C63FF')
        open(os.path.join(outdir,name+'.svg'),'w',encoding='utf-8').write(svg)
        print('ok', name, len(svg))
