/**
 * Web UI audit driver and recorder using Playwright.
 */

import { Page, Locator } from "@playwright/test";
import * as fs from "fs";

export interface ElementSnapshot {
  id: string;
  kind: string;
  x: number;
  y: number;
  width: number;
  height: number;
  enabled: boolean;
}

export class WebAuditDriver {
  private page: Page;
  private interactions: any[] = [];
  private seq = 0;

  constructor(page: Page) {
    this.page = page;
  }

  async find(id: string): Promise<Locator> {
    const locator = this.page.locator(`[data-testid="${id}"], #${id}`);
    const count = await locator.count();
    if (count === 0) {
      throw new Error(`Control '${id}' not found`);
    }
    if (count > 1) {
      throw new Error(`Multiple controls matched ID '${id}'`);
    }
    return locator.first();
  }

  async real_click(handle: Locator, expectDisabled = false): Promise<void> {
    const isEnabled = await handle.isEnabled();
    if (!isEnabled && !expectDisabled) {
      throw new Error("Control is disabled");
    }
    const id = (await handle.getAttribute("data-testid")) || "elem";
    if (isEnabled) {
      await handle.click();
    }
    this.seq += 1;
    this.interactions.push({
      control_id: id,
      input_kind: "mouse",
      trusted: true,
      control_state: isEnabled ? "enabled" : "disabled",
      sequence_number: this.seq,
    });
  }

  async snapshot(): Promise<ElementSnapshot[]> {
    return await this.page.evaluate(() => {
      const results: ElementSnapshot[] = [];
      const elems = document.querySelectorAll("[data-testid], button, input, select, a");
      elems.forEach((el) => {
        const rect = el.getBoundingClientRect();
        results.push({
          id: el.getAttribute("data-testid") || el.id || "elem",
          kind: el.tagName.toLowerCase(),
          x: rect.x,
          y: rect.y,
          width: rect.width,
          height: rect.height,
          enabled: !(el as HTMLButtonElement).disabled,
        });
      });
      return results;
    });
  }

  saveEvidence(path = "ui_evidence.json"): void {
    const payload = {
      run_id: "web_run",
      framework: "web",
      interactions: this.interactions,
      cases: [],
      layout_findings: [],
    };
    fs.writeFileSync(path, JSON.stringify(payload, null, 2), "utf-8");
  }
}
