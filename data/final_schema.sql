CREATE schema capstone;

CREATE TABLE capstone.dim_date (
  date_id date NOT NULL,
  month_name character varying,
  day_name character varying,
  season character varying,
  year integer,
  week_number smallint,
  CONSTRAINT dim_date_pkey PRIMARY KEY (date_id)
);
CREATE TABLE capstone.dim_geo (
  geo_id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  geo_name text NOT NULL,
  geo_level text NOT NULL DEFAULT 'UNKNOWN'::text CHECK (geo_level = ANY (ARRAY['PROVINCE'::text, 'COUNTRY'::text, 'CITY'::text, 'UNKNOWN'::text])),
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT dim_geo_pkey PRIMARY KEY (geo_id)
);
CREATE TABLE capstone.dim_product (
  product_id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  product_name text NOT NULL,
  category text,
  unit_id bigint,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT dim_product_pkey PRIMARY KEY (product_id),
  CONSTRAINT dim_product_default_unit_id_fkey FOREIGN KEY (unit_id) REFERENCES capstone.dim_unit(unit_id)
);
CREATE TABLE capstone.dim_source (
  source_id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  source_name text NOT NULL,
  source_type text NOT NULL DEFAULT 'UNKNOWN'::text CHECK (source_type = ANY (ARRAY['INTERNAL'::text, 'GOVERNMENT'::text, 'SCRAPING'::text, 'UNKNOWN'::text])),
  frequency text NOT NULL DEFAULT 'UNKNOWN'::text CHECK (frequency = ANY (ARRAY['DAILY'::text, 'WEEKLY'::text, 'MONTHLY'::text, 'UNKNOWN'::text])),
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT dim_source_pkey PRIMARY KEY (source_id)
);
CREATE TABLE capstone.dim_unit (
  unit_id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  unit_base text NOT NULL CHECK (unit_base = ANY (ARRAY['kg'::text, 'l'::text, 'unit'::text, 'dozen'::text, 'other'::text])),
  unit_desc text,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT dim_unit_pkey PRIMARY KEY (unit_id)
);
CREATE TABLE capstone.dim_vendor (
  vendor_id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  vendor_name text NOT NULL,
  vendor_type text NOT NULL DEFAULT 'UNKNOWN'::text CHECK (vendor_type = ANY (ARRAY['SUPPLIER'::text, 'RETAILER'::text, 'WHOLESALER'::text, 'GOVERNMENT'::text, 'UNKNOWN'::text])),
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT dim_vendor_pkey PRIMARY KEY (vendor_id)
);
CREATE TABLE capstone.fact_market_price (
  market_fact_id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  date_id date NOT NULL,
  geo_id bigint NOT NULL,
  vendor_id bigint NOT NULL,
  source_id bigint NOT NULL,
  product_id bigint NOT NULL,
  unit_id bigint,
  price_base real NOT NULL CHECK (price_base >= 0::numeric::double precision),
  source_product_key text,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT fact_market_price_pkey PRIMARY KEY (market_fact_id),
  CONSTRAINT fact_market_price_date_id_fkey FOREIGN KEY (date_id) REFERENCES capstone.dim_date(date_id),
  CONSTRAINT fact_market_price_geo_id_fkey FOREIGN KEY (geo_id) REFERENCES capstone.dim_geo(geo_id),
  CONSTRAINT fact_market_price_vendor_id_fkey FOREIGN KEY (vendor_id) REFERENCES capstone.dim_vendor(vendor_id),
  CONSTRAINT fact_market_price_source_id_fkey FOREIGN KEY (source_id) REFERENCES capstone.dim_source(source_id),
  CONSTRAINT fact_market_price_product_id_fkey FOREIGN KEY (product_id) REFERENCES capstone.dim_product(product_id),
  CONSTRAINT fact_market_price_unit_id_fkey FOREIGN KEY (unit_id) REFERENCES capstone.dim_unit(unit_id)
);
CREATE TABLE capstone.fact_purchase_line (
  purchase_fact_id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  date_id date NOT NULL,
  vendor_id bigint NOT NULL,
  product_id bigint NOT NULL,
  invoice_id text,
  line_id text,
  qty real NOT NULL CHECK (qty >= 0::numeric::double precision),
  qty_base real,
  unit_id bigint,
  unit_price real NOT NULL CHECK (unit_price >= 0::numeric::double precision),
  unit_price_base real,
  line_total numeric NOT NULL CHECK (line_total >= 0::numeric),
  source_id bigint NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT fact_purchase_line_pkey PRIMARY KEY (purchase_fact_id),
  CONSTRAINT fact_purchase_line_date_id_fkey FOREIGN KEY (date_id) REFERENCES capstone.dim_date(date_id),
  CONSTRAINT fact_purchase_line_vendor_id_fkey FOREIGN KEY (vendor_id) REFERENCES capstone.dim_vendor(vendor_id),
  CONSTRAINT fact_purchase_line_product_id_fkey FOREIGN KEY (product_id) REFERENCES capstone.dim_product(product_id),
  CONSTRAINT fact_purchase_line_unit_id_fkey FOREIGN KEY (unit_id) REFERENCES capstone.dim_unit(unit_id),
  CONSTRAINT fact_purchase_line_source_id_fkey FOREIGN KEY (source_id) REFERENCES capstone.dim_source(source_id)
);
CREATE TABLE capstone.product_alias (
  alias_id bigint GENERATED ALWAYS AS IDENTITY NOT NULL,
  source_id bigint NOT NULL,
  product_id bigint NOT NULL,
  source_product_key text NOT NULL,
  source_product_name text,
  unit_id bigint,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT product_alias_pkey PRIMARY KEY (alias_id),
  CONSTRAINT product_alias_source_id_fkey FOREIGN KEY (source_id) REFERENCES capstone.dim_source(source_id),
  CONSTRAINT product_alias_product_id_fkey FOREIGN KEY (product_id) REFERENCES capstone.dim_product(product_id),
  CONSTRAINT product_alias_unit_id_fkey FOREIGN KEY (unit_id) REFERENCES capstone.dim_unit(unit_id)
);