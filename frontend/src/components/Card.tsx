import type { ReactNode } from "react";

export type Accent = "s1" | "s2" | "s3" | "s4";

interface CardProps {
  title?: string;
  accent?: Accent;
  actions?: ReactNode;
  className?: string;
  children: ReactNode;
}

export function Card({ title, accent = "s1", actions, className = "", children }: CardProps) {
  return (
    <section className={`card card-${accent} ${className}`}>
      {(title || actions) && (
        <header className="card-head">
          {title && <h2>{title}</h2>}
          {actions}
        </header>
      )}
      {children}
    </section>
  );
}
