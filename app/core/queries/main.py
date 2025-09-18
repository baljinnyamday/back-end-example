class Queries:
    get_images = """
        SELECT 
                r.id, 
                COALESCE(r.edited_dp_name, f.drawpoint_name) AS drawpoint_name,
                r.created_date,
                COALESCE(f.new_fine_area, r.fine_area) AS fine_area,
                COALESCE(f.new_small_area, r.small_area) AS small_area,
                COALESCE(f.new_medium_area, r.medium_area) AS medium_area,
                COALESCE(f.new_large_area, r.large_area) AS large_area,
                COALESCE(f.new_oversized_area, r.oversized_area) AS oversized_area,
                r.raw_image_path,
                r.predicted_image_path,
                COALESCE(r.bbox_image_path, r.raw_image_path) AS bbox_image_path,
                f.wetness,
                f.dp_condition,
                f.drawpointconditioncomment,
                f.fragmentationcomment,
                f.wetnesscomment,
                r.is_edited,
                r.image_status,
                r.has_bund,
                r.imagetaken_date,
                COALESCE(f.username, '') AS username
            FROM fragmentation_images r
            LEFT JOIN approved_fragmentation f ON r.id = f.image_id
            WHERE r.image_status != 'submitted'
    ORDER BY r.created_date DESC
    LIMIT $1
    OFFSET $2;
    """

    get_all_img = """
        SELECT 
                r.id, 
                COALESCE(r.edited_dp_name, f.drawpoint_name) AS drawpoint_name,
                r.created_date,
                r.image_status
            FROM fragmentation_images r
            LEFT JOIN approved_fragmentation f ON r.id = f.image_id
            WHERE r.image_status != 'submitted'
    ORDER BY r.created_date DESC
    """

    get_history = """
                    SELECT 
                        r.id, 
                        COALESCE(r.edited_dp_name, r.drawpoint_name) AS drawpoint_name,
                        r.created_date ,
                        COALESCE(f.new_fine_area, r.fine_area) AS fine_area,
                        COALESCE(f.new_small_area, r.small_area) AS small_area,
                        COALESCE(f.new_medium_area, r.medium_area) AS medium_area,
                        COALESCE(f.new_large_area, r.large_area) AS large_area,
                        COALESCE(f.new_oversized_area, r.oversized_area) AS oversized_area,
                        r.raw_image_path,
                        r.predicted_image_path,
                        COALESCE(f.username, '') AS username
                    FROM fragmentation_images r
                    LEFT JOIN approved_fragmentation f ON r.id = f.image_id
                    WHERE r.image_status = 'submitted'
                    ORDER BY created_date DESC
                """

    delete_image = """
        DELETE FROM fragmentation_images WHERE id = $1;
    """

    delete_from_approved_images = """
        DELETE FROM approved_fragmentation WHERE image_id = $1;
    """

    get_image_by_id = """
        SELECT * FROM fragmentation_images WHERE id = $1;
    """
