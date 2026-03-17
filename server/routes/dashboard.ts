import { Router } from "express";
import { db, items, movements, stock, projectSites, warehouses, assetUnits } from "../db/index.js";
import { sql, desc, gte, and, eq, sum } from "drizzle-orm";

const router = Router();

function requireAuth(req: any, res: any, next: any) {
  if (!req.isAuthenticated()) return res.status(401).json({ error: "Not authenticated" });
  next();
}

router.get("/stats", requireAuth, async (req, res) => {
  try {
    const [itemCount] = await db.select({ count: sql<number>`count(*)` }).from(items).where(eq(items.isActive, true));
    const [whCount] = await db.select({ count: sql<number>`count(*)` }).from(warehouses).where(eq(warehouses.isActive, true));
    const [siteCount] = await db.select({ count: sql<number>`count(*)` }).from(projectSites).where(eq(projectSites.status, "active"));
    const [moveCount] = await db.select({ count: sql<number>`count(*)` }).from(movements);
    
    // Total inventory value
    const stockRows = await db.select({
      quantity: stock.quantity,
      unitCost: items.unitCost,
    }).from(stock).leftJoin(items, eq(stock.itemId, items.id));
    const totalValue = stockRows.reduce((acc, row) => acc + (parseFloat(row.quantity || "0") * parseFloat(row.unitCost || "0")), 0);
    
    // Low stock items
    const allItems = await db.select().from(items).where(eq(items.isActive, true));
    let lowStockCount = 0;
    for (const item of allItems) {
      if (item.itemType === "asset") {
        const ct = await db.select({ count: sql<number>`count(*)` }).from(assetUnits)
          .where(and(eq(assetUnits.itemId, item.id), eq(assetUnits.locationType, "warehouse")));
        if (parseFloat(ct[0].count as any) < parseFloat(item.reorderLevel || "0")) lowStockCount++;
      } else {
        const [tot] = await db.select({ total: sql<string>`coalesce(sum(quantity),0)` }).from(stock).where(eq(stock.itemId, item.id));
        if (parseFloat(tot.total) < parseFloat(item.reorderLevel || "0")) lowStockCount++;
      }
    }
    
    res.json({
      items: Number(itemCount.count),
      warehouses: Number(whCount.count),
      activeSites: Number(siteCount.count),
      movements: Number(moveCount.count),
      totalValue: totalValue.toFixed(2),
      lowStock: lowStockCount,
    });
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

router.get("/recent-movements", requireAuth, async (_req, res) => {
  try {
    const rows = await db.select({
      id: movements.id,
      movementType: movements.movementType,
      date: movements.date,
      quantity: movements.quantity,
      reference: movements.reference,
      itemId: movements.itemId,
      itemName: items.name,
      itemSku: items.sku,
    }).from(movements)
      .leftJoin(items, eq(movements.itemId, items.id))
      .orderBy(desc(movements.date))
      .limit(10);
    res.json(rows);
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

router.get("/chart/movements", requireAuth, async (_req, res) => {
  try {
    const days: { date: string; delivery: number; transfer: number; pullout: number; consumption: number }[] = [];
    for (let i = 6; i >= 0; i--) {
      const d = new Date();
      d.setDate(d.getDate() - i);
      const dateStr = d.toISOString().slice(0, 10);
      const start = new Date(dateStr + "T00:00:00Z");
      const end = new Date(dateStr + "T23:59:59Z");
      const rows = await db.select({
        type: movements.movementType,
        count: sql<number>`count(*)`,
      }).from(movements)
        .where(and(gte(movements.date, start), sql`${movements.date} <= ${end}`))
        .groupBy(movements.movementType);
      const entry: any = { date: dateStr, delivery: 0, transfer: 0, pullout: 0, consumption: 0 };
      for (const r of rows) {
        if (r.type in entry) entry[r.type] = Number(r.count);
      }
      days.push(entry);
    }
    res.json(days);
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

router.get("/low-stock", requireAuth, async (_req, res) => {
  try {
    const allItems = await db.select().from(items).where(eq(items.isActive, true));
    const result = [];
    for (const item of allItems) {
      let qty = 0;
      if (item.itemType === "asset") {
        const [ct] = await db.select({ count: sql<number>`count(*)` }).from(assetUnits)
          .where(and(eq(assetUnits.itemId, item.id), sql`status != 'scrapped'`));
        qty = Number(ct.count);
      } else {
        const [tot] = await db.select({ total: sql<string>`coalesce(sum(quantity),0)` }).from(stock).where(eq(stock.itemId, item.id));
        qty = parseFloat(tot.total);
      }
      if (qty < parseFloat(item.reorderLevel || "0")) {
        result.push({ id: item.id, sku: item.sku, name: item.name, unit: item.unit, itemType: item.itemType, qty, reorderLevel: item.reorderLevel });
      }
    }
    res.json(result.slice(0, 10));
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

export default router;
