import { bootstrapApplication } from "@angular/platform-browser";
import { appConfig } from "./app/app.config";
import { AppComponent } from "./app/app.component";

bootstrapApplication(AppComponent, appConfig)
  .then(() => {
    if ("serviceWorker" in navigator) {
      window.addEventListener("load", () => {
        const swUrl = new URL("sw.js", document.baseURI).href;
        const scope = new URL("./", document.baseURI).href;
        navigator.serviceWorker
          .register(swUrl, { scope })
          .catch((err) =>
            console.warn("No se pudo registrar el Service Worker:", err)
          );
      });
    }
  })
  .catch((err) => console.error(err));
