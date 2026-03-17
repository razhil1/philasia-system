import { Router } from "express";
import { db, requests, requestItems, items, projectSites, users, movements, stock } from "../db/index.js";
import { eq, desc, and, sql } from "drizzle-orm";

const router = Router();
const auth = (req: any, res: any, next: any) => { if (!req.isAuthenticated()) return res.status(401).json({ error: "Not authenticated" }); next(); };

router.get("/", auth, async (req, res) => {
  try {
    const rows = await db.select({
      id: requests.id, status: requests.status, priority: requests.priority,
      createdAt: requests.createdAt, dateNeeded: requests.dateNeeded,
      siteName: projectSites.name, username: users.username, notes: requests.notes,
    }).from(requests)
      .leftJoin(projectSites, eq(requests.siteId, projectSites.id))
      .leftJoin(users, eq(requests.userId, users.id))
      .orderBy(desc(requests.createdAt));
    res.json(rows);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.get("/:id", auth, async (req, res) => {
  try {
    const [req_] = await db.select({
      id: requests.id, status: requests.status, priority: requests.priority,
      createdAt: requests.createdAt, dateNeeded: requests.dateNeeded, notes: requests.notes,
      rejectionReason: requests.rejectionReason, approvedAt: requests.approvedAt,
      siteId: requests.siteId, siteName: projectSites.name,
      userId: requests.userId, username: users.username,
    }).from(requests)
      .leftJoin(projectSites, eq(requests.siteId, projectSites.id))
      .leftJoin(users, eq(requests.userId, users.id))
      .where(eq(requests.id, parseInt(req.params.id)));
    if (!req_) return res.status(404).json({ error: "Not found" });
    const reqItems = await db.select({
      id: requestItems.id, itemId: requestItems.itemId, itemName: items.name, itemSku: items.sku,
      unit: items.unit, quantityRequested: requestItems.quantityRequested,
      quantityDelivered: requestItems.quantityDelivered, notes: requestItems.notes,
    }).from(requestItems).leftJoin(items, eq(requestItems.itemId, items.id))
      .where(eq(requestItems.requestId, req_.id));
    res.json({ ...req_, items: reqItems });
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.post("/", auth, async (req, res) => {
  try {
    const u = req.user as any;
    const { siteId, dateNeeded, priority, notes, reqItems } = req.body;
    const [request] = await db.insert(requests).values({
      siteId: parseInt(siteId), userId: u.id, dateNeeded: dateNeeded || null,
      priority: priority || "normal", notes: notes || null, status: "pending",
    }).returning();
    if (reqItems?.length) {
      await db.insert(requestItems).values(reqItems.map((i: any) => ({
        requestId: request.id, itemId: parseInt(i.itemId),
        quantityRequested: i.quantityRequested.toString(), notes: i.notes || null,
      })));
    }
    res.json(request);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.post("/:id/approve", auth, async (req, res) => {
  try {
    const u = req.user as any;
    const [row] = await db.update(requests).set({ status: "approved", approvedAt: new Date(), approvedById: u.id })
      .where(eq(requests.id, parseInt(req.params.id))).returning();
    res.json(row);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.post("/:id/reject", auth, async (req, res) => {
  try {
    const [row] = await db.update(requests).set({ status: "rejected", rejectionReason: req.body.reason || null })
      .where(eq(requests.id, parseInt(req.params.id))).returning();
    res.json(row);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

router.post("/:id/fulfill", auth, async (req, res) => {
  try {
    const u = req.user as any;
    const { warehouseId, fulfillItems } = req.body;
    const [request] = await db.select().from(requests).where(eq(requests.id, parseInt(req.params.id)));
    if (!request) return res.status(404).json({ error: "Not found" });
    
    for (const fi of fulfillItems) {
      const qty = parseFloat(fi.quantity);
      if (qty <= 0) continue;
      // Create movement
      await db.insert(movements).values({
        movementType: "transfer", itemId: parseInt(fi.itemId), quantity: qty.toString(),
        fromLocationType: "warehouse", fromWarehouseId: parseInt(warehouseId),
        toLocationType: "site", toSiteId: request.siteId,
        reference: `REQ-${request.id}`, userId: u.id,
      });
      // Update stock
      await db.execute(sql`UPDATE stock SET quantity = quantity - ${qty} WHERE item_id=${fi.itemId} AND warehouse_id=${warehouseId} AND location_type='warehouse'`);
      await db.execute(sql`
        INSERT INTO stock (item_id, location_type, site_id, quantity) VALUES (${fi.itemId},'site',${request.siteId},${qty})
        ON CONFLICT DO NOTHING
      `);
      await db.execute(sql`UPDATE stock SET quantity = quantity + ${qty} WHERE item_id=${fi.itemId} AND site_id=${request.siteId} AND location_type='site'`);
      await db.update(requestItems).set({ quantityDelivered: sql`quantity_delivered + ${qty}` })
        .where(and(eq(requestItems.requestId, request.id), eq(requestItems.itemId, parseInt(fi.itemId))));
    }
    const [updated] = await db.update(requests).set({ status: "fulfilled" }).where(eq(requests.id, request.id)).returning();
    res.json(updated);
  } catch (err: any) { res.status(500).json({ error: err.message }); }
});

export default router;
