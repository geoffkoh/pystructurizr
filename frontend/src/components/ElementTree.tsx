import { useState } from "react";
import type { Container, SoftwareSystem, Workspace } from "../types";

interface ElementTreeProps {
  workspace: Workspace | null;
}

/** A collapsible section header row with a chevron. */
function Toggle({
  open,
  label,
  color,
  onToggle,
}: {
  open: boolean;
  label: string;
  color?: string;
  onToggle: () => void;
}) {
  return (
    <button type="button" className="tree__toggle" onClick={onToggle}>
      <span className={"tree__chevron" + (open ? " tree__chevron--open" : "")}>
        ▶
      </span>
      {color ? (
        <span className="dot" style={{ background: color }} aria-hidden />
      ) : null}
      <span>{label}</span>
    </button>
  );
}

function ContainerNode({ container }: { container: Container }) {
  const [open, setOpen] = useState(true);
  const hasComponents = container.components.length > 0;
  return (
    <li>
      {hasComponents ? (
        <Toggle
          open={open}
          color="#43a047"
          label={container.name}
          onToggle={() => setOpen((v) => !v)}
        />
      ) : (
        <div className="tree__leaf">
          <span className="dot" style={{ background: "#43a047" }} /> {container.name}
        </div>
      )}
      {hasComponents && open ? (
        <ul>
          {container.components.map((component) => (
            <li key={component.id} className="tree__leaf">
              <span className="dot" style={{ background: "#fb8c00" }} />{" "}
              {component.name}
              {component.technology ? (
                <span className="tree__tech"> · {component.technology}</span>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
    </li>
  );
}

function SystemNode({ system }: { system: SoftwareSystem }) {
  const [open, setOpen] = useState(true);
  const hasContainers = system.containers.length > 0;
  return (
    <li>
      {hasContainers ? (
        <Toggle
          open={open}
          color="#1976d2"
          label={system.name}
          onToggle={() => setOpen((v) => !v)}
        />
      ) : (
        <div className="tree__leaf">
          <span className="dot" style={{ background: "#1976d2" }} /> {system.name}
        </div>
      )}
      {hasContainers && open ? (
        <ul>
          {system.containers.map((container) => (
            <ContainerNode key={container.id} container={container} />
          ))}
        </ul>
      ) : null}
    </li>
  );
}

/**
 * Renders the workspace model as a collapsible tree:
 * people, then software systems -> containers -> components.
 */
export function ElementTree({ workspace }: ElementTreeProps) {
  const [peopleOpen, setPeopleOpen] = useState(true);
  const [systemsOpen, setSystemsOpen] = useState(true);

  if (!workspace) {
    return (
      <section className="section">
        <h2 className="section__title">Elements</h2>
        <p className="muted">Load a file to explore its elements.</p>
      </section>
    );
  }

  const { people, software_systems } = workspace.model;

  return (
    <section className="section">
      <h2 className="section__title">Elements</h2>
      <ul className="tree">
        <li>
          <Toggle
            open={peopleOpen}
            label={`People (${people.length})`}
            onToggle={() => setPeopleOpen((v) => !v)}
          />
          {peopleOpen ? (
            <ul>
              {people.length === 0 ? (
                <li className="tree__leaf muted">None</li>
              ) : (
                people.map((person) => (
                  <li key={person.id} className="tree__leaf">
                    <span className="dot" style={{ background: "#0d47a1" }} />{" "}
                    {person.name}
                  </li>
                ))
              )}
            </ul>
          ) : null}
        </li>
        <li>
          <Toggle
            open={systemsOpen}
            label={`Software Systems (${software_systems.length})`}
            onToggle={() => setSystemsOpen((v) => !v)}
          />
          {systemsOpen ? (
            <ul>
              {software_systems.length === 0 ? (
                <li className="tree__leaf muted">None</li>
              ) : (
                software_systems.map((system) => (
                  <SystemNode key={system.id} system={system} />
                ))
              )}
            </ul>
          ) : null}
        </li>
      </ul>
    </section>
  );
}
