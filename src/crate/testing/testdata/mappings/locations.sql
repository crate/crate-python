create table locations (
    "name" TEXT PRIMARY KEY,
    "date" TIMESTAMP WITH TIME ZONE,
    "datetime" TIMESTAMP WITH TIME ZONE,
    "nullable_datetime" TIMESTAMP WITH TIME ZONE,
    "nullable_date" TIMESTAMP WITH TIME ZONE,
    "time" TIME WITH TIME ZONE,
    "kind" TEXT,
    "flag" BOOLEAN,
    "position" INTEGER,
    "description" TEXT,
    "details" ARRAY(OBJECT)
) WITH (number_of_replicas=0)
