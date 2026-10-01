// Hilfen, um den React-Elementbaum eines Diagramms ohne DOM zu untersuchen.
// Recharts rendert ohne Browser kein SVG, darum werden die Props der Recharts-Elemente geprüft.
import { isValidElement, type ReactElement, type ReactNode } from "react";

type AnyElement = ReactElement<Record<string, unknown>>;

export function findAll(node: ReactNode, type: unknown): AnyElement[] {
  const found: AnyElement[] = [];
  const visit = (child: ReactNode) => {
    if (Array.isArray(child)) return child.forEach(visit);
    if (!isValidElement(child)) return;
    const element = child as AnyElement;
    if (element.type === type) found.push(element);
    visit(element.props.children as ReactNode);
    // ChartTooltip übergibt den Inhalt als Prop, nicht als Kind.
    if (isValidElement(element.props.content)) visit(element.props.content as ReactNode);
  };
  visit(node);
  return found;
}

export function findOne(node: ReactNode, type: unknown): AnyElement {
  const found = findAll(node, type);
  if (found.length !== 1) throw new Error(`Erwartet genau ein Element, gefunden: ${found.length}`);
  return found[0];
}
