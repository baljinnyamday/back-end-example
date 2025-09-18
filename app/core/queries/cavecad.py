class CavecadQueries:
    retreive_query = """
                    SELECT fine_area, small_area, medium_area, large_area, oversized_area
                    FROM fragmentation_images
                    WHERE id = $1
                    """

    update = """
                UPDATE fragmentation_images 
                SET 
                    is_edited = $1,
                    image_status = 'submitted',
                    updated_date = $2
                WHERE id = $3
                """
    count = """
                SELECT COUNT(*) FROM approved_fragmentation WHERE image_id = $1
                """

    final_update = """
                    UPDATE approved_fragmentation 
                    SET 
                        new_fine_area = $1, 
                        new_small_area = $2, 
                        new_medium_area = $3, 
                        new_large_area = $4, 
                        new_oversized_area = $5, 
                        dp_condition = $6, 
                        bund    = $7, 
                        wetness = $8, 
                        username = $9,
                        drawpoint_name = $10,
                        submitted_date = $11,
                        created_date = $12,
                        drawpointconditioncomment = $13,
                        fragmentationcomment = $14,
                        wetnesscomment = $15
                    WHERE image_id = $16
                    """

    insert = """
                    INSERT INTO approved_fragmentation (
                        image_id, 
                        new_fine_area, 
                        new_small_area, 
                        new_medium_area, 
                        new_large_area, 
                        new_oversized_area, 
                        dp_condition, 
                        bund, 
                        wetness, 
                        username,
                        drawpoint_name,
                        submitted_date,
                        drawpointconditioncomment,
                        fragmentationcomment,
                        wetnesscomment,
                        created_date
            
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                    """
