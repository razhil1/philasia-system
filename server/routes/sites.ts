import { Router } from "express";
import { db, projectSites, stock, items, assetUnits } from "../db/index.js";
import { eq, and, sql } from "drizzle-orm";

const router = Router();
const auth = (req: any, res: any, next: any) => { if (!req.isAuthenticated()) return res.status(401).json({ error: "Not authenticated" }); next(); };

router.get("/", auth, async (_req, res) => {
  try {
    const rows = await db.select().from(projectSites).orderBy(projectSites.name);
    const enriched = await Promise.all(rows.map(async (site) => {
      const [stockSum] = await db.select({ val: sql<string>`coalesce(sum(s.quantity * i.unit_cost),0)` })
        .from(stock).leftJoin(items, eq(stock.itemId, items.id))
        .where(and(eq(stock.siteId, site.id), eq(stock.locationType, "site")));
      const [assetCount] = await db.select({ count: sql<number>`count(*)` }).from(assetUnits)
        .where(and(eq(assetUnits.locationId, site.id), eq(assetUnits.locationType, "site")));
      return { ...site, materialsValue: parseFloat(stockSum?.val || "0"), deployedAssets: Number(assetCount?.count || 0) };
    }));
    res.json(enriched);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.get("/:id", auth, async (req, res) => {
  try {
    const [site] = await db.select().from(projectSites).where(eq(projectSites.id, parseInt(req.params.id)));
    if (!site) return res.status(404).json({ error: "Not found" });
    const materialStock = await db.select({ itemId: stock.itemId, quantity: stock.quantity, name: items.name, sku: items.sku, unit: items.unit, unitCost: items.unitCost })
      .from(stock).leftJoin(items, eq(stock.itemId, items.id))
      .where(and(eq(stock.siteId, site.id), eq(stock.locationType, "site")));
    const deployedUnits = await db.select().from(assetUnits)
      .where(and(eq(assetUnits.locationId, site.id), eq(assetUnits.locationType, "site")));
    res.json({ ...site, materials: materialStock, deployedAssets: deployedUnits });
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.post("/", auth, async (req, res) => {
  try {
    const { name, address, client, startDate, endDate, status, contactPerson, contactPhone, budget, notes } = req.body;
    const [row] = await db.insert(projectSites).values({ name, address, client, startDate: startDate || null, endDate: endDate || null, status: status || "planned", contactPerson, contactPhone, budget: budget || "0", notes }).returning();
    res.json(row);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.put("/:id", auth, async (req, res) => {
  try {
    const { name, address, client, startDate, endDate, status, contactPerson, contactPhone, budget, notes } = req.body;
    const [row] = await db.update(projectSites).set({ name, address, client, startDate: startDate || null, endDate: endDate || null, status, contactPerson, contactPhone, budget: budget || "0", notes }).where(eq(projectSites.id, parseInt(req.params.id))).returning();
    res.json(row);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

export default router;
