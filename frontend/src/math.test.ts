import {describe,it,expect} from 'vitest';
import {previewMath} from './math';
describe('MathML input preview',()=>{
 it('renders fractions, powers, radicals and implicit multiplication',()=>{
  expect(previewMath('1/2')).toContain('<mfrac>');
  expect(previewMath('2x^2')).toContain('<msup>');
  expect(previewMath('sqrt(9)')).toContain('<msqrt>');
  expect(previewMath('(x+1)(x-1)')).toContain('<mrow>');
 });
 it('does not render assignments, arbitrary functions, or markup',()=>{
  expect(previewMath('x=2')).toBeNull();
  expect(previewMath('evil(2)')).toBeNull();
  expect(previewMath('<script>alert(1)</script>')).toBeNull();
  expect(previewMath('')).toBeNull();
 });
});
