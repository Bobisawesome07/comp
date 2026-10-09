import { create, parseDependencies, type MathNode } from 'mathjs';

const {parse} = create({parseDependencies});

const escape = (value: string) => value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');
const wrap = (tag: string, value: string) => `<${tag}>${value}</${tag}>`;

/** Presentation only: never evaluate the user's expression in the browser. */
export function previewMath(input: string): string | null {
  if (!input.trim() || input.length > 160) return null;
  try {
    let count = 0;
    function render(node: MathNode): string {
      if (++count > 85) throw new Error('Too complex');
      const n = node as MathNode & {value?: number|string; name?: string; args?: MathNode[]; op?: string; content?: MathNode; fn?: MathNode};
      if (n.type === 'ConstantNode') return wrap('mn', escape(String(n.value)));
      if (n.type === 'SymbolNode') return wrap('mi', escape(n.name === 'pi' ? 'π' : n.name || ''));
      if (n.type === 'ParenthesisNode') return wrap('mrow', wrap('mo','(') + render(n.content!) + wrap('mo',')'));
      if (n.type === 'OperatorNode') {
        const args = n.args!.map(render);
        if (n.op === '/' && args.length === 2) return wrap('mfrac', args.join(''));
        if (n.op === '^' && args.length === 2) return wrap('msup', args.join(''));
        if (args.length === 1) return wrap('mrow', wrap('mo', escape(n.op!)) + args[0]);
        return wrap('mrow', args.join(wrap('mo', escape(n.op === '*' ? '·' : n.op!))));
      }
      if (n.type === 'FunctionNode' && n.fn?.type === 'SymbolNode' && n.args?.length === 1) {
        const name = (n.fn as MathNode & {name:string}).name;
        if (!['sqrt','sin','cos','tan','abs','log','exp'].includes(name)) throw new Error('Unsupported');
        const arg = render(n.args[0]);
        if (name === 'sqrt') return wrap('msqrt',arg);
        if (name === 'abs') return wrap('mrow',wrap('mo','|')+arg+wrap('mo','|'));
        return wrap('mrow',wrap('mi',name)+wrap('mo','(')+arg+wrap('mo',')'));
      }
      throw new Error('Unsupported notation');
    }
    return `<math xmlns="http://www.w3.org/1998/Math/MathML" display="block">${render(parse(input.replaceAll('−','-').replaceAll('×','*').replaceAll('÷','/').replaceAll('π','pi')))}</math>`;
  } catch { return null; }
}
