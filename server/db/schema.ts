import { pgTable, serial, varchar, text, integer, numeric, boolean, timestamp, date } from "drizzle-orm/pg-core";

export const users = pgTable("user", {
  id: serial("id").primaryKey(),
  username: varchar("username", { length: 64 }).notNull().unique(),
  email: varchar("email", { length: 120 }).notNull().unique(),
  passwordHash: varchar("password_hash", { length: 256 }),
  fullName: varchar("full_name", { length: 150 }),
  role: varchar("role", { length: 30 }).default("viewer").notNull(),
  isActive: boolean("is_active").default(true),
  createdAt: timestamp("created_at").defaultNow(),
  lastLogin: timestamp("last_login"),
});

export const categories = pgTable("category", {
  id: serial("id").primaryKey(),
  name: varchar("name", { length: 100 }).notNull(),
  description: text("description"),
  parentId: integer("parent_id"),
});

export const items = pgTable("item", {
  id: serial("id").primaryKey(),
  sku: varchar("sku", { length: 50 }).notNull().unique(),
  name: varchar("name", { length: 200 }).notNull(),
  description: text("description"),
  categoryId: integer("category_id"),
  unit: varchar("unit", { length: 30 }).notNull(),
  unitCost: numeric("unit_cost", { precision: 12, scale: 2 }).default("0"),
  reorderLevel: numeric("reorder_level", { precision: 10, scale: 2 }).default("0"),
  itemType: varchar("item_type", { length: 20 }).default("consumable").notNull(),
  photo: varchar("photo", { length: 255 }),
  isActive: boolean("is_active").default(true),
  createdAt: timestamp("created_at").defaultNow(),
});

export const warehouses = pgTable("warehouse", {
  id: serial("id").primaryKey(),
  name: varchar("name", { length: 100 }).notNull(),
  location: varchar("location", { length: 255 }),
  contactPerson: varchar("contact_person", { length: 100 }),
  contactInfo: text("contact_info"),
  isActive: boolean("is_active").default(true),
  createdAt: timestamp("created_at").defaultNow(),
});

export const projectSites = pgTable("project_site", {
  id: serial("id").primaryKey(),
  name: varchar("name", { length: 100 }).notNull(),
  address: text("address"),
  client: varchar("client", { length: 100 }),
  startDate: date("start_date"),
  endDate: date("end_date"),
  status: varchar("status", { length: 20 }).default("planned"),
  contactPerson: varchar("contact_person", { length: 100 }),
  contactPhone: varchar("contact_phone", { length: 50 }),
  budget: numeric("budget", { precision: 14, scale: 2 }).default("0"),
  notes: text("notes"),
  createdAt: timestamp("created_at").defaultNow(),
});

export const stock = pgTable("stock", {
  id: serial("id").primaryKey(),
  locationType: varchar("location_type", { length: 20 }).notNull(),
  warehouseId: integer("warehouse_id"),
  siteId: integer("site_id"),
  itemId: integer("item_id").notNull(),
  quantity: numeric("quantity", { precision: 10, scale: 2 }).default("0"),
  lastUpdated: timestamp("last_updated").defaultNow(),
});

export const movements = pgTable("movement", {
  id: serial("id").primaryKey(),
  movementType: varchar("movement_type", { length: 20 }).notNull(),
  date: timestamp("date").defaultNow(),
  fromLocationType: varchar("from_location_type", { length: 20 }),
  fromWarehouseId: integer("from_warehouse_id"),
  fromSiteId: integer("from_site_id"),
  toLocationType: varchar("to_location_type", { length: 20 }),
  toWarehouseId: integer("to_warehouse_id"),
  toSiteId: integer("to_site_id"),
  itemId: integer("item_id").notNull(),
  quantity: numeric("quantity", { precision: 10, scale: 2 }).notNull(),
  unitCost: numeric("unit_cost", { precision: 12, scale: 2 }).default("0"),
  reference: varchar("reference", { length: 100 }),
  notes: text("notes"),
  userId: integer("user_id").notNull(),
  requestId: integer("request_id"),
});

export const requests = pgTable("request", {
  id: serial("id").primaryKey(),
  siteId: integer("site_id").notNull(),
  userId: integer("user_id").notNull(),
  dateNeeded: date("date_needed"),
  priority: varchar("priority", { length: 20 }).default("normal"),
  status: varchar("status", { length: 20 }).default("pending"),
  notes: text("notes"),
  rejectionReason: text("rejection_reason"),
  createdAt: timestamp("created_at").defaultNow(),
  approvedAt: timestamp("approved_at"),
  approvedById: integer("approved_by_id"),
});

export const requestItems = pgTable("request_item", {
  id: serial("id").primaryKey(),
  requestId: integer("request_id").notNull(),
  itemId: integer("item_id").notNull(),
  quantityRequested: numeric("quantity_requested", { precision: 10, scale: 2 }).notNull(),
  quantityDelivered: numeric("quantity_delivered", { precision: 10, scale: 2 }).default("0"),
  notes: varchar("notes", { length: 200 }),
});

export const assetUnits = pgTable("asset_unit", {
  id: serial("id").primaryKey(),
  itemId: integer("item_id").notNull(),
  assetTag: varchar("asset_tag", { length: 50 }).notNull().unique(),
  serialNumber: varchar("serial_number", { length: 100 }),
  status: varchar("status", { length: 20 }).default("available").notNull(),
  condition: varchar("condition", { length: 20 }).default("good").notNull(),
  locationType: varchar("location_type", { length: 20 }).default("warehouse"),
  locationId: integer("location_id"),
  acquiredDate: date("acquired_date"),
  notes: text("notes"),
  createdAt: timestamp("created_at").defaultNow(),
});
