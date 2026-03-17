import { Router } from "express";
import { db, items, stock, movements, warehouses, projectSites, categories } from "../db/index.js";
import { eq, desc, and, gte, lte, sql } from "drizzle-orm";

const router = Router();
const auth = (req: any, res: any, next: any) => { if (!req.isAuthenticated()) return res.status(401).json({ error: "Not authenticated" }); next(); };

router.get("/stock", auth, async (_req, res) => {
  try {
    const allItems = await db.select({ id: items.id, sku: items.sku, name: items.name, unit: items.unit, unitCost: items.unitCost, reorderLevel: items.reorderLevel, itemType: items.itemType, categoryName: categories.name })
      .from(items).leftJoin(categories, eq(items.categoryId, categories.id)).where(eq(items.isActive, true)).orderBy(items.name);
    const allWarehouses = await db.select().from(warehouses).where(eq(warehouses.isActive, true));
    const allSites = await db.select().from(projectSites);
    const stockRows = await db.select().from(stock);
    
    const matrix = allItems.map((item) => {
      const stockMap: any = {};
      for (const wh of allWarehouses) {
        const s = stockRows.find(r => r.itemId === item.id && r.locationType === "warehouse" && r.warehouseId === wh.id);
        stockMap[`wh_${wh.id}`] = parseFloat(s?.quantity || "0");
      }
      for (const site of allSites) {
        const s = stockRows.find(r => r.itemId === item.id && r.locationType === "site" && r.siteId === site.id);
        stockMap[`site_${site.id}`] = parseFloat(s?.quantity || "0");
      }
      const total = Object.values(stockMap).reduce((a: any, b: any) => a + b, 0) as number;
      return { ...item, stockMap, total, isLow: total < parseFloat(item.reorderLevel || "0") };
    });
    res.json({ items: matrix, warehouses: allWarehouses, sites: allSites });
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.get("/movements", auth, async (req, res) => {
  try {
    const { type, dateFrom, dateTo } = req.query as any;
    const conditions: any[] = [];
    if (type) conditions.push(eq(movements.movementType, type));
    if (dateFrom) conditions.push(gte(movements.date, new Date(dateFrom)));
    if (dateTo) conditions.push(lte(movements.date, new Date(dateTo + "T23:59:59")));
    const rows = await db.select({ id: movements.id, movementType: movements.movementType, date: movements.date, quantity: movements.quantity, unitCost: movements.unitCost, reference: movements.reference, itemName: items.name, itemSku: items.sku })
      .from(movements).leftJoin(items, eq(movements.itemId, items.id))
      .where(conditions.length ? and(...conditions) : undefined).orderBy(desc(movements.date)).limit(1000);
    res.json(rows);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.get("/low-stock", auth, async (_req, res) => {
  try {
    const allItems = await db.select().from(items).where(eq(items.isActive, true));
    const result = [];
    for (const item of allItems) {
      const [tot] = await db.select({ total: sql<string>`coalesce(sum(quantity),0)` }).from(stock).where(eq(stock.itemId, item.id));
      const qty = parseFloat(tot.total);
      if (qty < parseFloat(item.reorderLevel || "0")) result.push({ ...item, currentQty: qty });
    }
    res.json(result);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

export default router;
