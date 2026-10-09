export interface Session {code:string; player_id:string; token:string}
export interface Config {game:'mansion'|'math'; pace:'relaxed'|'timed'|'pressure'; subject:string}
export interface Player {id:string; name:string; online:boolean; ready:boolean}
export interface Part {text?:string; mathml?:string}
export interface Puzzle {id:string; title:string; room?:number; story?:string; format?:string; clues?:string[]; revealed?:string[]; votes?:string[]; instruction?:string; parts?:Part[]; generator?:string}
export interface Result {title:string; answer?:string; solved:boolean; parts?:Part[]; instruction?:string}
export interface State {code:string; host:string; you:string; status:'lobby'|'playing'|'won'|'lost'; config:Config; players:Player[]; index:number; total:number; score:number; bonus:number; mistakes:number; hints_used:number; elapsed:number; remaining:number|null; paused:boolean; cooldown:number; chat:{id:string; player_id:string; name:string; text:string; time:number}[]; reason:string|null; keys:{number:number; digit:string}[]; current:Puzzle|null; results:Result[]}
