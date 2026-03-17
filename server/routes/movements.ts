import { Router } from "express";
import { db, movements, items, warehouses, projectSites, stock, users } from "../db/index.js";
import { eq, desc, and, gte, lte, sql } from "drizzle-orm";

const router = Router();
const auth = (req: any, res: any, next: any) => { if (!req.isAuthenticated()) return res.status(401).json({ error: "Not authenticated" }); next(); };

async function updateStock(itemId: number, locType: string, locId: number | null, delta: number) {
  if (!locId || locType === "external" || locType === "none") return;
  const whereClause = locType === "warehouse"
    ? and(eq(stock.itemId, itemId), eq(stock.locationType, locType), eq(stock.warehouseId, locId))
    : and(eq(stock.itemId, itemId), eq(stock.locationType, locType), eq(stock.siteId, locId));
  const existing = await db.select().from(stock).where(whereClause).limit(1);
  if (existing.length) {
    await db.update(stock).set({ quantity: sql`${stock.quantity} + ${delta}`, lastUpdated: new Date() }).where(whereClause);
  } else {
    const vals: any = { itemId, locationType: locType, quantity: delta.toString(), lastUpdated: new Date() };
    if (locType === "warehouse") vals.warehouseId = locId;
    else vals.siteId = locId;
    await db.insert(stock).values(vals);
  }
}

router.get("/", auth, async (req, res) => {
  try {
    const { type, itemId, dateFrom, dateTo, page = "1", limit = "50" } = req.query as any;
    const conditions: any[] = [];
    if (type) conditions.push(eq(movements.movementType, type));
    if (itemId) conditions.push(eq(movements.itemId, parseInt(itemId)));
    if (dateFrom) conditions.push(gte(movements.date, new Date(dateFrom)));
    if (dateTo) conditions.push(lte(movements.date, new Date(dateTo + "T23:59:59")));

    const offset = (parseInt(page) - 1) * parseInt(limit);
    const rows = await db.select({
      id: movements.id, movementType: movements.movementType, date: movements.date,
      quantity: movements.quantity, unitCost: movements.unitCost, reference: movements.reference,
      notes: movements.notes, itemId: movements.itemId, itemName: items.name, itemSku: items.sku,
      fromLocationType: movements.fromLocationType, fromWarehouseId: movements.fromWarehouseId,
      fromSiteId: movements.fromSiteId, toLocationType: movements.toLocationType,
      toWarehouseId: movements.toWarehouseId, toSiteId: movements.toSiteId,
      userId: movements.userId, username: users.username, userFullName: users.fullName,
    }).from(movements)
      .leftJoin(items, eq(movements.itemId, items.id))
      .leftJoin(users, eq(movements.userId, users.id))
      .where(conditions.length ? and(...conditions) : undefined)
      .orderBy(desc(movements.date))
      .limit(parseInt(limit)).offset(offset);

    const [{ count }] = await db.select({ count: sql<number>`count(*)` }).from(movements)
      .where(conditions.length ? and(...conditions) : undefined);

    res.json({ data: rows, total: Number(count), page: parseInt(page), limit: parseInt(limit) });
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.post("/", auth, async (req, res) => {
  try {
    const u = req.user as any;
    const { movementType, itemId, quantity, unitCost, fromLocationType, fromWarehouseId, fromSiteId, toLocationType, toWarehouseId, toSiteId, reference, notes } = req.body;
    const qty = parseFloat(quantity);
    const iid = parseInt(itemId);

    const [movement] = await db.insert(movements).values({
      movementType, itemId: iid, quantity: qty.toString(), unitCost: unitCost || "0",
      fromLocationType: fromLocationType || null, fromWarehouseId: fromWarehouseId ? parseInt(fromWarehouseId) : null,
      fromSiteId: fromSiteId ? parseInt(fromSiteId) : null,
      toLocationType: toLocationType || null, toWarehouseId: toWarehouseId ? parseInt(toWarehouseId) : null,
      toSiteId: toSiteId ? parseInt(toSiteId) : null,
      reference: reference || null, notes: notes || null, userId: u.id,
    }).returning();

    // Update stock
    if (fromLocationType && fromLocationType !== "external" && fromLocationType !== "none") {
      const fromId = fromLocationType === "warehouse" ? (fromWarehouseId ? parseInt(fromWarehouseId) : null) : (fromSiteId ? parseInt(fromSiteId) : null);
      await updateStock(iid, fromLocationType, fromId, -qty);
    }
    if (toLocationType && toLocationType !== "external" && toLocationType !== "none") {
      const toId = toLocationType === "warehouse" ? (toWarehouseId ? parseInt(toWarehouseId) : null) : (toSiteId ? parseInt(toSiteId) : null);
      await updateStock(iid, toLocationType, toId, qty);
    }

    res.json(movement);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

export default router;
