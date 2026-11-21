import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from "@angular/core";
import type { ObservatoryNavTab } from "../../models/limnimetro-block.model";

export interface ObservatoryNavItem {
  readonly id: ObservatoryNavTab;
  readonly label: string;
}

export const OBSERVATORY_NAV_ITEMS: readonly ObservatoryNavItem[] = [
  { id: "bloques", label: "Inicio" },
  { id: "niveles", label: "Niveles" },
  { id: "historico", label: "Histórico" },
  { id: "alertas", label: "Alertas" },
  { id: "calamar", label: "Calamar" },
];

@Component({
  selector: "app-bottom-nav",
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (variant() === "desktop-links") {
      <nav class="obs-top-nav" aria-label="Navegación del observatorio">
        @for (item of items; track item.id) {
          <button
            type="button"
            class="obs-top-nav-link"
            [class.is-active]="activeTab() === item.id"
            [class.is-alert-item]="item.id === 'alertas' && hasActiveAlert()"
            [attr.aria-current]="activeTab() === item.id ? 'page' : null"
            (click)="selectTab(item.id)"
          >
            {{ item.label }}
          </button>
        }
      </nav>
    } @else {
      <nav class="obs-bottom-nav" aria-label="Navegación principal móvil">
        @for (item of items; track item.id) {
          <button
            type="button"
            class="obs-bottom-nav-btn"
            [class.is-active]="activeTab() === item.id"
            [class.is-alert-item]="item.id === 'alertas' && hasActiveAlert()"
            [attr.aria-current]="activeTab() === item.id ? 'page' : null"
            (click)="selectTab(item.id)"
          >
            <span class="obs-bottom-nav-icon" aria-hidden="true">
              @switch (item.id) {
                @case ("bloques") {
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="3" y="3" width="18" height="7" rx="1.5" />
                    <rect x="3" y="14" width="18" height="7" rx="1.5" />
                  </svg>
                }
                @case ("niveles") {
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M4 16c2-2 4-2 6 0s4 2 6 0 4-2 4 0" />
                    <path d="M4 11c2-2 4-2 6 0s4 2 6 0 4-2 4 0" />
                    <path d="M12 3v5" />
                    <path d="M9.5 5.5 12 3l2.5 2.5" />
                  </svg>
                }
                @case ("historico") {
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M3 3v18h18" />
                    <path d="M7 14l4-4 3 3 5-6" />
                  </svg>
                }
                @case ("alertas") {
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M12 3 2.8 19a1.2 1.2 0 0 0 1.04 1.8h16.32A1.2 1.2 0 0 0 21.2 19L12 3Z" />
                    <path d="M12 9.5v4.5" />
                    <circle cx="12" cy="17" r=".8" fill="currentColor" stroke="none" />
                  </svg>
                }
                @case ("calamar") {
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M12 21s7-5.8 7-11a7 7 0 1 0-14 0c0 5.2 7 11 7 11Z" />
                    <circle cx="12" cy="10" r="2.4" />
                  </svg>
                }
              }
            </span>
            <span class="obs-bottom-nav-label">{{ item.label }}</span>
          </button>
        }
      </nav>
    }
  `,
})
export class BottomNavComponent {
  readonly activeTab = input.required<ObservatoryNavTab>();
  readonly variant = input<"mobile-bar" | "desktop-links">("mobile-bar");
  readonly hasActiveAlert = input<boolean>(false);
  readonly tabChange = output<ObservatoryNavTab>();

  readonly items = OBSERVATORY_NAV_ITEMS;

  selectTab(tab: ObservatoryNavTab): void {
    this.tabChange.emit(tab);
  }
}
