import { Router } from "express";
import { db, warehouses, stock, items } from "../db/index.js";
import { eq, and, sql } from "drizzle-orm";

const router = Router();
const auth = (req: any, res: any, next: any) => { if (!req.isAuthenticated()) return res.status(401).json({ error: "Not authenticated" }); next(); };

router.get("/", auth, async (_req, res) => {
  try {
    const rows = await db.select().from(warehouses).where(eq(warehouses.isActive, true)).orderBy(warehouses.name);
    const enriched = await Promise.all(rows.map(async (wh) => {
      const stockRows = await db.select({ qty: sql<string>`coalesce(sum(s.quantity),0)`, val: sql<string>`coalesce(sum(s.quantity * i.unit_cost),0)` })
        .from(stock).leftJoin(items, eq(stock.itemId, items.id))
        .where(and(eq(stock.warehouseId, wh.id), eq(stock.locationType, "warehouse")));
      return { ...wh, totalQty: parseFloat(stockRows[0]?.qty || "0"), totalValue: parseFloat(stockRows[0]?.val || "0") };
    }));
    res.json(enriched);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.get("/:id", auth, async (req, res) => {
  try {
    const [wh] = await db.select().from(warehouses).where(eq(warehouses.id, parseInt(req.params.id)));
    if (!wh) return res.status(404).json({ error: "Not found" });
    const stockRows = await db.select({ itemId: stock.itemId, quantity: stock.quantity, name: items.name, sku: items.sku, unit: items.unit, unitCost: items.unitCost, itemType: items.itemType })
      .from(stock).leftJoin(items, eq(stock.itemId, items.id))
      .where(and(eq(stock.warehouseId, wh.id), eq(stock.locationType, "warehouse")));
    res.json({ ...wh, stock: stockRows });
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.post("/", auth, async (req, res) => {
  try {
    const { name, location, contactPerson, contactInfo } = req.body;
    const [row] = await db.insert(warehouses).values({ name, location, contactPerson, contactInfo }).returning();
    res.json(row);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.put("/:id", auth, async (req, res) => {
  try {
    const { name, location, contactPerson, contactInfo, isActive } = req.body;
    const [row] = await db.update(warehouses).set({ name, location, contactPerson, contactInfo, isActive }).where(eq(warehouses.id, parseInt(req.params.id))).returning();
    res.json(row);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

export default router;
