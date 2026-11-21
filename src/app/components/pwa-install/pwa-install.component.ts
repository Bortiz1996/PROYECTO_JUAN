import {
  ChangeDetectionStrategy,
  Component,
  OnDestroy,
  OnInit,
  computed,
  signal,
} from "@angular/core";

interface BeforeInstallPromptEvent extends Event {
  readonly platforms: string[];
  readonly userChoice: Promise<{
    outcome: "accepted" | "dismissed";
    platform: string;
  }>;
  prompt(): Promise<void>;
}

@Component({
  selector: "app-pwa-install",
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (isOffline()) {
      <div class="pwa-offline-bar" role="status">
        Modo sin conexión · Mostrando la última información guardada en el
        dispositivo
      </div>
    }

    @if (canShowInstall()) {
      <div class="pwa-install-wrap">
        <button
          type="button"
          class="pwa-install-btn"
          (click)="onInstallClick()"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2.2"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
          <span>{{
            isIos() ? "Instalar en iPhone / iPad" : "Instalar aplicación"
          }}</span>
        </button>
      </div>
    }

    @if (showHelpModal()) {
      <div
        class="pwa-modal-backdrop"
        role="dialog"
        aria-modal="true"
        aria-labelledby="pwa-modal-title"
        (click)="closeModal()"
      >
        <div class="pwa-modal-card" (click)="$event.stopPropagation()">
          <div class="pwa-modal-header">
            <h4 id="pwa-modal-title">Instalar JUAN en tu teléfono</h4>
            <button
              type="button"
              class="pwa-modal-close"
              aria-label="Cerrar instrucciones"
              (click)="closeModal()"
            >
              ✕
            </button>
          </div>

          @if (isIos()) {
            <p class="pwa-modal-lead">
              En Safari de iPhone o iPad, sigue estos pasos para agregar la app a
              tu pantalla de inicio:
            </p>
            <ol class="pwa-modal-steps">
              <li>
                Toca el botón <strong>Compartir</strong> (cuadro con flecha
                hacia arriba) en la barra del navegador.
              </li>
              <li>
                Desliza hacia abajo y selecciona
                <strong>Agregar a pantalla de inicio</strong>.
              </li>
              <li>Toca <strong>Agregar</strong> en la esquina superior.</li>
            </ol>
          } @else if (isEmbeddedFrame()) {
            <p class="pwa-modal-lead">
              Estás viendo la app dentro de un marco embebido. Para instalarla
              en el teléfono:
            </p>
            <ol class="pwa-modal-steps">
              <li>
                Abre la dirección directa de JUAN en Chrome, Edge o Safari de tu
                teléfono.
              </li>
              <li>
                Luego toca <strong>Instalar aplicación</strong> o el menú del
                navegador (⋮ → <em>Agregar a pantalla principal</em>).
              </li>
            </ol>
          } @else {
            <p class="pwa-modal-lead">
              Si el diálogo automático no apareció aún, puedes instalarla desde
              el menú de tu navegador:
            </p>
            <ol class="pwa-modal-steps">
              <li>
                Toca el menú del navegador (<strong>⋮</strong> arriba a la
                derecha en Chrome o Edge).
              </li>
              <li>
                Elige <strong>Instalar aplicación</strong> o
                <strong>Agregar a la pantalla principal</strong>.
              </li>
            </ol>
          }

          <div class="pwa-modal-actions">
            <button
              type="button"
              class="btn-action"
              (click)="closeModal()"
            >
              Entendido
            </button>
          </div>
        </div>
      </div>
    }
  `,
})
export class PwaInstallComponent implements OnInit, OnDestroy {
  readonly deferredPrompt = signal<BeforeInstallPromptEvent | null>(null);
  readonly isStandalone = signal<boolean>(false);
  readonly isIos = signal<boolean>(false);
  readonly isEmbeddedFrame = signal<boolean>(false);
  readonly isMobile = signal<boolean>(false);
  readonly isOffline = signal<boolean>(false);
  readonly showHelpModal = signal<boolean>(false);

  readonly canShowInstall = computed(() => {
    if (this.isStandalone()) return false;
    return (
      this.deferredPrompt() !== null || this.isIos() || this.isMobile()
    );
  });

  private standaloneMq: MediaQueryList | null = null;

  private readonly onBeforeInstallPrompt = (event: Event) => {
    event.preventDefault();
    this.deferredPrompt.set(event as BeforeInstallPromptEvent);
  };

  private readonly onAppInstalled = () => {
    this.deferredPrompt.set(null);
    this.isStandalone.set(true);
    this.showHelpModal.set(false);
  };

  private readonly onOnlineChange = () => {
    if (typeof navigator !== "undefined") {
      this.isOffline.set(!navigator.onLine);
    }
  };

  private readonly onDisplayModeChange = (event: MediaQueryListEvent) => {
    if (event.matches) {
      this.isStandalone.set(true);
      this.deferredPrompt.set(null);
    }
  };

  ngOnInit(): void {
    if (typeof window === "undefined") return;

    const nav = navigator as Navigator & { standalone?: boolean };
    const ua = nav.userAgent || "";

    this.isIos.set(
      /iphone|ipad|ipod/i.test(ua) ||
        (nav.platform === "MacIntel" && nav.maxTouchPoints > 1)
    );
    this.isMobile.set(/android|mobile|iphone|ipad|ipod/i.test(ua));
    this.isOffline.set(!nav.onLine);

    try {
      this.isEmbeddedFrame.set(window.self !== window.top);
    } catch {
      this.isEmbeddedFrame.set(true);
    }

    this.standaloneMq = window.matchMedia("(display-mode: standalone)");
    const standalone =
      this.standaloneMq.matches || Boolean(nav.standalone);
    this.isStandalone.set(standalone);

    this.standaloneMq.addEventListener("change", this.onDisplayModeChange);
    window.addEventListener("beforeinstallprompt", this.onBeforeInstallPrompt);
    window.addEventListener("appinstalled", this.onAppInstalled);
    window.addEventListener("online", this.onOnlineChange);
    window.addEventListener("offline", this.onOnlineChange);
  }

  ngOnDestroy(): void {
    if (typeof window === "undefined") return;
    this.standaloneMq?.removeEventListener("change", this.onDisplayModeChange);
    window.removeEventListener(
      "beforeinstallprompt",
      this.onBeforeInstallPrompt
    );
    window.removeEventListener("appinstalled", this.onAppInstalled);
    window.removeEventListener("online", this.onOnlineChange);
    window.removeEventListener("offline", this.onOnlineChange);
  }

  async onInstallClick(): Promise<void> {
    const promptEvent = this.deferredPrompt();
    if (!promptEvent) {
      this.showHelpModal.set(true);
      return;
    }

    try {
      await promptEvent.prompt();
      const { outcome } = await promptEvent.userChoice;
      if (outcome === "accepted") {
        this.deferredPrompt.set(null);
      }
    } catch {
      this.showHelpModal.set(true);
    }
  }

  closeModal(): void {
    this.showHelpModal.set(false);
  }
}
