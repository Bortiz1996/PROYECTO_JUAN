import { ChangeDetectionStrategy, Component } from "@angular/core";
import { ObservatoryShellComponent } from "./features/observatorio-juan/components/observatory-shell/observatory-shell.component";

@Component({
  selector: "app-root",
  imports: [ObservatoryShellComponent],
  templateUrl: "./app.component.html",
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AppComponent {}
