create table locations (
    name string primary key,
    date timestamp,
    datetime timestamp,
    kind string,
    position integer,
    description string,
    details array(object)
) with (number_of_replicas=0)
