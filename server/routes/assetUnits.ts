import { Router } from "express";
import { db, assetUnits, items, movements } from "../db/index.js";
import { eq, and, sql } from "drizzle-orm";

const router = Router();
const auth = (req: any, res: any, next: any) => { if (!req.isAuthenticated()) return res.status(401).json({ error: "Not authenticated" }); next(); };

router.get("/item/:itemId", auth, async (req, res) => {
  try {
    const rows = await db.select().from(assetUnits).where(eq(assetUnits.itemId, parseInt(req.params.itemId))).orderBy(assetUnits.status, assetUnits.assetTag);
    res.json(rows);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.post("/", auth, async (req, res) => {
  try {
    const { itemId, assetTag, serialNumber, status, condition, locationType, locationId, acquiredDate, notes } = req.body;
    const [row] = await db.insert(assetUnits).values({
      itemId: parseInt(itemId), assetTag, serialNumber: serialNumber || null,
      status: status || "available", condition: condition || "good",
      locationType: locationType || "warehouse", locationId: locationId ? parseInt(locationId) : null,
      acquiredDate: acquiredDate || null, notes: notes || null,
    }).returning();
    res.json(row);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.post("/bulk", auth, async (req, res) => {
  try {
    const { itemId, prefix, startNum, count, locationType, locationId, condition } = req.body;
    const created = [];
    for (let i = 0; i < Math.min(count, 100); i++) {
      const tag = `${prefix}-${String(startNum + i).padStart(3, "0")}`;
      const existing = await db.select().from(assetUnits).where(eq(assetUnits.assetTag, tag)).limit(1);
      if (!existing.length) {
        const [row] = await db.insert(assetUnits).values({
          itemId: parseInt(itemId), assetTag: tag, status: "available",
          condition: condition || "good", locationType: locationType || "warehouse",
          locationId: locationId ? parseInt(locationId) : null,
        }).returning();
        created.push(row);
      }
    }
    res.json({ created: created.length, units: created });
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.put("/:id", auth, async (req, res) => {
  try {
    const { assetTag, serialNumber, status, condition, locationType, locationId, notes, acquiredDate } = req.body;
    const [row] = await db.update(assetUnits).set({
      assetTag, serialNumber: serialNumber || null, status, condition,
      locationType, locationId: locationId ? parseInt(locationId) : null,
      notes: notes || null, acquiredDate: acquiredDate || null,
    }).where(eq(assetUnits.id, parseInt(req.params.id))).returning();
    res.json(row);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.post("/move", auth, async (req, res) => {
  try {
    const u = req.user as any;
    const { unitIds, movementType, toLocationType, toLocationId, condition, reference, notes } = req.body;
    const statusMap: Record<string, string> = {
      transfer: "deployed", pullout: "available", delivery: "available",
      maintenance: "maintenance", scrap: "scrapped",
    };
    const newStatus = statusMap[movementType] || "available";
    const [firstUnit] = await db.select().from(assetUnits).where(eq(assetUnits.id, unitIds[0]));
    const [item] = await db.select().from(items).where(eq(items.id, firstUnit.itemId));
    
    // Create a movement record for the batch
    const [movement] = await db.insert(movements).values({
      movementType, itemId: item.id, quantity: unitIds.length.toString(),
      fromLocationType: firstUnit.locationType || null,
      fromWarehouseId: firstUnit.locationType === "warehouse" ? firstUnit.locationId : null,
      fromSiteId: firstUnit.locationType === "site" ? firstUnit.locationId : null,
      toLocationType: toLocationType !== "none" ? toLocationType : "external",
      toWarehouseId: toLocationType === "warehouse" ? parseInt(toLocationId) : null,
      toSiteId: toLocationType === "site" ? parseInt(toLocationId) : null,
      reference: reference || null, notes: notes || null, userId: u.id,
    }).returning();

    for (const uid of unitIds) {
      await db.update(assetUnits).set({
        status: newStatus, condition: condition || undefined,
        locationType: toLocationType !== "none" ? toLocationType : firstUnit.locationType,
        locationId: toLocationType !== "none" ? parseInt(toLocationId) : firstUnit.locationId,
      }).where(eq(assetUnits.id, uid));
    }
    res.json({ movement, moved: unitIds.length });
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

export default router;
